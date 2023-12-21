import sys
import math
import time
import pathlib

# Local imports
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import scaleit_client


def _find_desired_replicas_count(current_replica_count, current_cpu_utilization, settings):
    target_avg_cpu_utilization_for_scale_out = settings.get('target_avg_cpu_utilization_for_scale_out')
    desired_replicas_count = math.ceil(current_replica_count * (current_cpu_utilization / target_avg_cpu_utilization_for_scale_out))
    return desired_replicas_count

def _need_to_cooldown(cooldown_lock_file, settings):
    log = settings.get('log')
    cool_down_time_seconds = settings.get('cool_down_time_seconds')
    log.debug(f'Reading cooldown {cooldown_lock_file} lock file.')
    try:
        with open(cooldown_lock_file) as fh:
            last_cooldown_time = fh.read().strip()
            last_cooldown_time = float(last_cooldown_time)
            seconds_from_last_scaler_action = time.time() - last_cooldown_time
            seconds_from_last_scaler_action = math.floor(seconds_from_last_scaler_action)
            if seconds_from_last_scaler_action < cool_down_time_seconds:
                log.info(f'Need to cooldown, auto-scaler will ignore any scale-out/in. Last scale action executed {seconds_from_last_scaler_action} secs before (cooldown: {cool_down_time_seconds} secs)')
                return True
            else:
                log.debug(f'No need to cooldown, last scale action executed {seconds_from_last_scaler_action} secs before (cooldown: {cool_down_time_seconds} secs)')
    except Exception as e:
        log.debug(f'Unable to read {cooldown_lock_file} cooldown lock file, will scale anyway, error - {e}')
    return False

def _verify_desired_replicas_count(desired_replicas_count, settings):
    log = settings.get('log')
    max_replicas = settings.get('max_replicas')
    min_replicas = settings.get('min_replicas')
    log.info(f'Desired replicas {desired_replicas_count} must be between min: {min_replicas}, max: {max_replicas}')
    return min(max(desired_replicas_count, min_replicas), max_replicas)
    
def _record_scale_action_time(cooldown_lock_file, settings):
    log = settings.get('log')
    try:
        with open(cooldown_lock_file, 'w') as fh:
            fh.write(str(time.time()))
    except Exception as e:
        log.debug(f'Unable to record scale time in cooldown lock file {cooldown_lock_file}, error - {e}')
    return     
    
def scale_app_replicas(current_replica_count, current_cpu_utilization, settings, dry_run):
    log = settings.get('log')
    cooldown_lock_file = settings.get('cooldown_lock_file')
    max_replicas = settings.get('max_replicas')
    min_replicas = settings.get('min_replicas')
    desired_replicas_count = _find_desired_replicas_count(current_replica_count, current_cpu_utilization, settings)
    log.info(f'Desired replicas: {desired_replicas_count}, Current replicas: {current_replica_count}, Min replicas: {min_replicas}, Max replicas: {max_replicas}')
    need_to_cooldown = _need_to_cooldown(cooldown_lock_file=cooldown_lock_file, settings=settings)
    if need_to_cooldown:
        log.debug('No need to run auto-scaler.')
        return current_replica_count
    log.debug('Auto-scaler is checking...')
    limit_verified_desired_replicas_count = _verify_desired_replicas_count(desired_replicas_count, settings)
    if limit_verified_desired_replicas_count > current_replica_count:
        log.info(f'Scale-out is required by delta: +{limit_verified_desired_replicas_count-current_replica_count} ({current_replica_count}->{limit_verified_desired_replicas_count})')
        if not dry_run:
            _scale_out_replicas(limit_verified_desired_replicas_count, current_replica_count, settings)
            return limit_verified_desired_replicas_count
    elif limit_verified_desired_replicas_count < current_replica_count:
        flapping_limit_verified_desired_replicas_count = _verify_scale_in_activity(limit_verified_desired_replicas_count, current_replica_count, current_cpu_utilization, settings)
        if flapping_limit_verified_desired_replicas_count:
            log.info(f'Scale-in is required by delta: {flapping_limit_verified_desired_replicas_count - current_replica_count} ({current_replica_count}->{flapping_limit_verified_desired_replicas_count})')
            if not dry_run:
                _scale_in_replicas(flapping_limit_verified_desired_replicas_count, current_replica_count, settings)
                return flapping_limit_verified_desired_replicas_count 
    else:
        autoscale_engine_runs_every = settings.get('autoscale_engine_runs_every')
        log.debug(f'No scale-out/scale-in, Will re-evaluate after {autoscale_engine_runs_every} secs.')
    return current_replica_count
    
def _scale_out_replicas(desired_replicas_count, current_replica_count, settings):
    log = settings.get('log')
    cooldown_lock_file = settings.get('cooldown_lock_file')
    log.info(f'Scaling-out by delta: +{desired_replicas_count - current_replica_count} ({current_replica_count}->{desired_replicas_count})')
    done = scaleit_client.update_app_replicas(replicas=desired_replicas_count, settings=settings)
    if done:
        _record_scale_action_time(cooldown_lock_file=cooldown_lock_file, settings=settings)
    return 
    
def _scale_in_replicas(desired_replicas_count, current_replica_count, settings):
    log = settings.get('log')
    cooldown_lock_file = settings.get('cooldown_lock_file')
    log.info(f'Scaling-in by delta: {desired_replicas_count - current_replica_count} ({current_replica_count}->{desired_replicas_count})')
    done = scaleit_client.update_app_replicas(replicas=desired_replicas_count, settings=settings)
    if done:
        _record_scale_action_time(cooldown_lock_file=cooldown_lock_file, settings=settings)
    return 
    
def _verify_scale_in_activity(desired_replicas_count, current_replica_count, current_cpu_utilization, settings):
    log = settings.get('log')
    log.info('Checking if scale-in can potentially cause flapping...')
    target_avg_cpu_utilization_for_scale_out = settings.get('target_avg_cpu_utilization_for_scale_out')
    target_avg_cpu_utilization_for_scale_in = settings.get('target_avg_cpu_utilization_for_scale_in')
    current_cpu_utilization_total = current_cpu_utilization * current_replica_count
    while desired_replicas_count < current_replica_count:
        effective_cpu_utilization_after_scale_in = current_cpu_utilization_total / desired_replicas_count
        effective_cpu_utilization_after_scale_in = round(effective_cpu_utilization_after_scale_in, 2)
        log.debug(f'Effective Avg CPU after Scale-in: {effective_cpu_utilization_after_scale_in} (CPU: {target_avg_cpu_utilization_for_scale_in}-{target_avg_cpu_utilization_for_scale_out}), Purposed desired replicas: {desired_replicas_count}')
        if effective_cpu_utilization_after_scale_in >= target_avg_cpu_utilization_for_scale_out:
            log.debug(f'Scaling-in to {desired_replicas_count} can make Avg CPU: {effective_cpu_utilization_after_scale_in} (>= {target_avg_cpu_utilization_for_scale_out})')
            log.debug(f'Scaling-in to {desired_replicas_count} is ignored by the auto-scaler to avoid flapping.')
            desired_replicas_count = desired_replicas_count + 1
            log.debug(f'Re-calculating effective CPU after scale-in with replicas: {desired_replicas_count} (+1) ({desired_replicas_count -1}->{desired_replicas_count})')
        else:
            log.info(f'Effective Avg CPU after Scale-in: {effective_cpu_utilization_after_scale_in} (CPU: {target_avg_cpu_utilization_for_scale_in}-{target_avg_cpu_utilization_for_scale_out}), Verified desired replicas: {desired_replicas_count}')
            return desired_replicas_count
    autoscale_engine_runs_every = settings.get('autoscale_engine_runs_every')
    log.info(f'No scale-in to avoid flapping, Will re-evaluate after {autoscale_engine_runs_every} secs.')
    return None

import time

# Local imports
import modules.app_autoscale as app_autoscale
import modules.scaleit_client as scaleit_client
import modules.settings as settings
from modules.logger import get_logger


configs =  settings.settings(sys_config='etc/system_settings.cfg', user_config='etc/user_settings.cfg')
autoscale_engine_runs_every = configs.get('autoscale_engine_runs_every')
log =  get_logger(logger_name=__name__, settings=configs)
configs['log'] = log
                             


def main():
    try:
        while True:
            current_cpu_utilization, current_replica_count = scaleit_client.find_current_cpu_stats(settings=configs)
            if current_cpu_utilization and current_replica_count:
                app_autoscale.scale_app_replicas(current_replica_count=current_replica_count,
                                                 current_cpu_utilization=current_cpu_utilization, dry_run=False,
                                                 settings=configs)
            else:
                log.warning('Auto Scaler execution skipped, check stats API return values.')
            log.info(f'Next check will be after {autoscale_engine_runs_every} seconds.')
            log.info('_____________________________________________________________________________\n\n')
            time.sleep(autoscale_engine_runs_every)
    except KeyboardInterrupt:
        log.warning('User you have pressed ctrl-c button.')


if __name__ == '__main__':
    main()

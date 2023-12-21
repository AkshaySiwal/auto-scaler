import time
import random
import requests


def _add_randomness_multiplier_for_wait_time(retry_add_randomness):
    if not retry_add_randomness:
        return 1
    return 1 +  random.random()

def _waiting_time(attempt, retry_after_seconds, retry_exponentially, settings):
    retry_add_randomness = settings.get('retry_add_randomness')
    if not retry_exponentially:
        # Not remmended but still adding this feature if needed.
        waiting_time = retry_after_seconds * _add_randomness_multiplier_for_wait_time(retry_add_randomness)
        return round(waiting_time, 2)
    waiting_time = ( retry_after_seconds ** attempt ) * _add_randomness_multiplier_for_wait_time(retry_add_randomness)
    return round(waiting_time, 2)
    
def _get_app_status_read_url(settings):
    app_status_port=settings.get('app_status_port')
    app_status_host=settings.get('app_status_host')
    app_status_read_url=settings.get('app_status_read_url')
    app_status_secure=settings.get('app_status_secure')
    app_status_host.rstrip('/')
    if app_status_host.startswith('http'):
        return f'{app_status_host}:{app_status_port}{app_status_read_url}'
    if app_status_secure:
        return f'https://{app_status_host}:{app_status_port}{app_status_read_url}'
    return f'http://{app_status_host}:{app_status_port}{app_status_read_url}'

def find_current_cpu_stats(settings):
    log = settings.get('log')
    url = _get_app_status_read_url(settings)
    read_metrics_key = settings.get('read_metrics_key')
    read_replicas_key=settings.get('read_replicas_key')
    app_connection_timeout=settings.get('app_connection_timeout')
    attempts = settings.get('api_retries_count')
    headers = {'Accept' : 'application/json'}
    for n in range(1, attempts + 1):
        try:
            response = requests.get(url=url, headers=headers, timeout=app_connection_timeout)
            response.raise_for_status()
            data = response.json()
            try:
                avg_cpu = _read_nested_key_value(read_metrics_key, data)
                replicas= _read_nested_key_value(read_replicas_key, data) 
                # This is to make sure we always return a float, even if the API returns a numeric value as a string, e.g., '33.7'.
                # The API currently returns an integer or float, but this block checks if the API returns something other than these data types.
                # In the future version, if the response changes, it will handle any primitive data type change but will throw an error if the complete response structure changes.
                avg_cpu = float(avg_cpu)  
                replicas = int(replicas)
            except ValueError as e:
                # This will be executed if the API returns a non-supported value.
                log.error(f'{url} returned {response.status_code}, Avg CPU/Replicas: Non-supported value returned')
                log.debug(f'{url} returned {response.status_code}, Response: {data}')
                avg_cpu = None
                replicas = None
            finally:
                log.debug(f'{url} returned {response.status_code}, Avg CPU: {avg_cpu}, Replicas: {replicas}')
                return avg_cpu, replicas
        except requests.exceptions.HTTPError as e:
            http_status_prefix =  e.response.status_code // 100
            retry_on_http_codes = settings.get('retry_on_http_codes')
            if http_status_prefix in retry_on_http_codes:
                _attempt_appropriate_wait_and_logging(total_attempts=attempts, current_attempt=n, url=url, error_string=e.response.status_code, settings=settings)
                continue
            log.error(f'{url} returned {e.response.status_code}. No retry configured, giving up.')
            return None, None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            retry_on_connection_error = settings.get('retry_on_connection_error') 
            if retry_on_connection_error:
                _attempt_appropriate_wait_and_logging(total_attempts=attempts, current_attempt=n, url=url, error_string='ConnectionError/TimeOut', settings=settings)
                continue
            log.error(f'Unable to connect to API {url}, check if API endpoint is correct. No retry configured, giving up. error {e}')
            return None, None
        except Exception as e:
            log.error(f'Unable to call API {url}, error {e}')
            return None, None
    log.error(f'All re-tries were excusted for {url}, giving up.')
    return None, None # When all attempts fail, this value will be returned.

def _get_replica_update_url(settings):
    app_status_port=settings.get('app_status_port')
    app_status_host=settings.get('app_status_host')
    app_replica_update_url=settings.get('app_replica_update_url')
    app_status_secure=settings.get('app_status_secure')
    app_status_host.rstrip('/')
    if app_status_host.startswith('http'):
        return f'{app_status_host}:{app_status_port}{app_replica_update_url}'
    if app_status_secure:
        return f'https://{app_status_host}:{app_status_port}{app_replica_update_url}'
    return f'http://{app_status_host}:{app_status_port}{app_replica_update_url}'

def update_app_replicas(replicas, settings):
    log = settings.get('log')
    url = _get_replica_update_url(settings)
    read_replicas_key = settings.get('read_replicas_key')
    app_connection_timeout=settings.get('app_connection_timeout')
    attempts = settings.get('api_retries_count')
    headers = {'Content-type' : 'application/json'}
    data = _make_nested_key_value(read_replicas_key, replicas)
    for n in range(1, attempts + 1):
        try:
            response = requests.put(url=url, headers=headers, json=data, timeout=app_connection_timeout)
            response.raise_for_status()
            log.info(f'{url} returned {response.status_code}, Scaled to replicas: {replicas}')
            return True
        except requests.exceptions.HTTPError as e:
            http_status_prefix =  e.response.status_code // 100
            retry_on_http_codes = settings.get('retry_on_http_codes')
            if http_status_prefix in retry_on_http_codes:
                _attempt_appropriate_wait_and_logging(total_attempts=attempts, current_attempt=n, url=url, error_string=e.response.status_code, settings=settings)
                continue
            log.error(f'{url} returned {e.response.status_code}. No retry configured, giving up.')
            return None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            retry_on_connection_error = settings.get('retry_on_connection_error') 
            if retry_on_connection_error:
                _attempt_appropriate_wait_and_logging(total_attempts=attempts, current_attempt=n, url=url, error_string='ConnectionError/TimeOut', settings=settings)
                continue
            log.error(f'Unable to connect to API {url}, check if API endpoint is correct. No retry configured, giving up. error {e}')
            return None
        except Exception as e:
            log.error(f'Unable to call API {url}, error {e}')
            return None
    log.error(f'All re-tries were excusted for {url}, giving up.')
    return None # When all attempts fail, this value will be returned.

def _attempt_appropriate_wait_and_logging(total_attempts, current_attempt, url, error_string, settings):
    log = settings.get('log')
    retry_after_seconds = settings.get('retry_after_seconds') 
    retry_exponentially = settings.get('retry_exponentially')
    if total_attempts > 1:
        time_to_sleep = _waiting_time(attempt=current_attempt, retry_after_seconds=retry_after_seconds, retry_exponentially=retry_exponentially, settings=settings )
        log.warning(f'{url} returned {error_string}, Attept {current_attempt}, Retrying after {time_to_sleep}')
        time.sleep(time_to_sleep)
    else:
        log.warning(f'{url} returned {error_string}, No retry configured.')
    return

def _read_nested_key_value(key_string, data):
    keys = key_string.split('.')
    for key in keys:
        data = data.get(key, {})
    return data

def _make_nested_key_value(key_string, value):
    data = {}
    keys = key_string.split('.')
    for key in keys:
        data[key] = {}
    data[key] = value
    return data

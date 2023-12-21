import matplotlib.pyplot as plt

# Local imports
import modules.scaleit_client as scaleit_client
from modules.logger import get_logger
import modules.settings as settings


configs =  settings.settings(sys_config='etc/system_settings.file', user_config='etc/user_settings.file')
graph_kpi_period = configs.get('graph_kpi_period')
log =  get_logger(logger_name=__name__, settings=configs)
configs['log'] = log


try:
    t = 0
    while True:
        t += 1
        current_cpu_utilization, current_replica_count = scaleit_client.find_current_cpu_stats(settings=configs)
        if current_cpu_utilization:
            plt.scatter(t, current_cpu_utilization)
            plt.pause(graph_kpi_period)
    plt.show()
except KeyboardInterrupt:
    log.warning('User you have pressed ctrl-c button.')
except Exception as e:
    log.error(f'Error - {e}')
finally:
    log.info('Graph END')

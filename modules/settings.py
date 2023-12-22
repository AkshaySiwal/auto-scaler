import json
from functools import lru_cache 


def _read_config(file):
    result = {}
    try:
        print(f'Reading config file - {file}')
        with open(file) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith('#'):
                    continue
                line = line.split("=")
                if len(line) > 1:
                    key = line[0].strip()
                    value = line[1].split('#')[0].strip()
                if key and value:
                    result[key] = value
    except Exception as e:
        print(f'Unable to reading config file - {file}, error - {e}')
    return result

def _write_config(file, data):
    try:
        print(f'Genrating effective config file - {file}')
        with open(file, 'w') as fh:
            for key, value in data.items():
                fh.write(f'{key}={value}\n')  
    except Exception as e:
        print(f'Unable to write config file - {file}, error - {e}')
    return 
               
@lru_cache
def get(name):
    configs = _read_config('etc/configs.cfg')
    return configs.get(name)

def settings(sys_config, user_config=None):
    configs = _read_config(sys_config)
    if user_config:
        user_config = _read_config(user_config)
        for key, value in user_config.items():
            configs[key] = value
    configs = _polish_values(configs)
    _write_config('etc/configs.cfg', configs)
    return configs

def _polish_values(data):
    result = {}
    for key, value in data.items():
        try:
            if value in ['False', 'false']:
                value = False
            elif value in ['True', 'true']:
                value = True
            else:
                value_temp = float(value)
                if '.' in value:
                    value = round(value_temp, 2)
                else:
                    value = int(value)
        except ValueError:
            value = value.strip('"').strip("'")
            if ( value.startswith('[') and value.endswith(']') ) or ( value.startswith('(') and value.endswith(')') ) or ( value.startswith('{') and value.endswith('}') ):
                value = json.loads(value)
        result[key] = value
    return result  

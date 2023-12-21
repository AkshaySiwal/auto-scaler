import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler


FORMATTER = logging.Formatter("%(asctime)s | %(levelname)-6.6s | %(funcName)30.30s:%(lineno)-4.4s |  %(message)s")


def _get_stream_handler():
   console_handler = logging.StreamHandler(sys.stdout)
   console_handler.setFormatter(FORMATTER)
   return console_handler

def _get_file_handler(log_file):
   file_handler = TimedRotatingFileHandler(log_file, when='midnight')
   file_handler.setFormatter(FORMATTER)
   return file_handler

def get_logger(logger_name, settings):
   log_file = settings.get('log_file')
   log_dir = settings.get('log_dir')
   log_level = settings.get('debug_logs')
   log_file_full_path = f'{log_dir}/{log_file}'
   _create_log_dir(log_dir)
   logger = logging.getLogger(logger_name)
   if log_level:
      logger.setLevel(logging.DEBUG)
   else:
      logger.setLevel(logging.INFO)
   logger.addHandler(_get_stream_handler())
   logger.addHandler(_get_file_handler(log_file_full_path))
   return logger

def _create_log_dir(log_dir):
   if not os.path.exists(log_dir):
      os.makedirs(log_dir)

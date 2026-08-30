import time
import logging

from custom_profiler import profiler, Interactivity
from custom_profiler import profiler_collecteur as pc

def options(filename='custom_profiler.log', # None = logger in csl ; False = logger in file
                 interactivity = Interactivity.AUTO, # ENABLE / MF_NO_INTERAC / DISABLE / AUTO / OFF
                 logger_name = ' ⚡', 
                 add_custom_level = False):

    pc.options(interactivity = interactivity # ENABLE / MF_NO_INTERAC / DISABLE / AUTO / OFF
              , use_logger = True
              , logger_name = logger_name
              , add_custom_level = add_custom_level
              , profiler_level = 25
              , force_print_in_console = False
              , no_summary_in_log = False)

    if filename:
        logging.basicConfig(filename=filename, filemode='w')
    else :
        logging.basicConfig()

    if add_custom_level :
        logger = logging.getLogger(logger_name).profiler
    else :
        logger = logging.getLogger(logger_name).info
    logger(" test logger")

    @profiler
    def my_func():
        a = [1] * (10 ** 6)
        b = [2] * (2 * 10 ** 7)  
        time.sleep(2)
        del b
        time.sleep(2)
        return a

    my_func()

def test_log_in_csl():
    options(filename=None # None = logger in csl ; False = no logger
            , logger_name = ' ⚡'
            , add_custom_level = True)

def test_log_in_file():
    options(filename='custom_profiler.log' # None = logger in csl ; False = no logger
            , logger_name = ' ⚡' 
            , add_custom_level = False)
    
def test_log_in_file_profLvl():
    options(filename='custom_profiler.log' # None = logger in csl ; False = no logger
            , logger_name = ' ⚡' 
            , add_custom_level = True)

if __name__ == "__main__":
    # test_log_in_csl()
    # logging.getLogger().handlers.pop()
    # test_log_in_file()
    test_log_in_file_profLvl()
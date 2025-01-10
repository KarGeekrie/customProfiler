import time
import logging

from custom_profiler import profiler, INTERACTIVITY_OPT_ENUM
from custom_profiler import profiler_collecteur as pc

def options(filename='custom_profiler.log', # None = logger in csl ; False = logger in file
                 interractivity = INTERACTIVITY_OPT_ENUM.AUTO, # ENABLE / MF_NO_INTERAC / DISABLE / AUTO
                 loggername = ' ⚡', 
                 addCustumLvl = False):

    pc.options(interractivity = interractivity # ENABLE / MF_NO_INTERAC / DISABLE / AUTO
              , useLogger = True
              , loggername = loggername
              , addCustumLvl = addCustumLvl
              , profilerlvl = 25
              , forcePrintInCsl = False
              , noSummaryInLog = False)

    if filename:
        logging.basicConfig(filename=filename, filemode='w')
    else :
        logging.basicConfig()

    if addCustumLvl :
        logger = logging.getLogger(loggername).profiler
    else :
        logger = logging.getLogger(loggername).info
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
            , loggername = ' ⚡'
            , addCustumLvl = True)

def test_log_in_file():
    options(filename='custom_profiler.log' # None = logger in csl ; False = no logger
            , loggername = ' ⚡' 
            , addCustumLvl = False)
    
def test_log_in_file_profLvl():
    options(filename='custom_profiler.log' # None = logger in csl ; False = no logger
            , loggername = ' ⚡' 
            , addCustumLvl = True)

if __name__ == "__main__":
    # test_log_in_csl()
    # logging.getLogger().handlers.pop()
    # test_log_in_file()
    test_log_in_file_profLvl()
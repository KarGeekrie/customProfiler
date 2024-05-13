import time
from custom_profiler import profiler, profiler_lbl, magic_profiler, profiler_collecteur, INTERACTIVITY_OPT_ENUM

@profiler
def my_func():
    a = [1] * (10 ** 6)
    b = [2] * (2 * 10 ** 7)  
    time.sleep(2)
    del b
    time.sleep(2)
    return a

a = my_func()

with magic_profiler("my_code_to_prof") :
    d = [1] * (10 ** 6)
    e = [2] * (2 * 10 ** 7)  
    time.sleep(3)
    del e

@profiler_lbl
def my_func():
    a = [1] * (10 ** 6)
    b = [2] * (2 * 10 ** 7)  
    time.sleep(2)
    del b
    time.sleep(2)
    return a

a = my_func()

"""
import logging

logging.basicConfig(filename='custom_profiler.log', filemode='w')

loggername = " ⚡" # logger name
addCustumLvl = False # add "PROFILER" level in logger

pc = profiler_collecteur()
pc.options(interractivity = INTERACTIVITY_OPT_ENUM.ENABLE # ENABLE / MF_NO_INTERAC / DISABLE / AUTO
          , useLogger = True
          , loggername = loggername
          , addCustumLvl = addCustumLvl
          , profilerlvl = 25)

#Log in consol
#ch = logging.StreamHandler()
#logger = logging.getLogger("⚡")
#logger.addHandler(ch)

#log in file
#logger.info('Finished')
#self.logger("strlog")

logger = logging.getLogger(loggername)
if addCustumLvl :
    logger.profiler(pc.__str__())
else :
    logger.info(pc.__str__())
"""
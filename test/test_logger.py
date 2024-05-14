import time
import logging

from custom_profiler import profiler, profiler_lbl, magic_profiler, profiler_collecteur, INTERACTIVITY_OPT_ENUM

def test_options(filename='custom_profiler.log', # None = logger in csl ; False = no logger
                 interractivity = INTERACTIVITY_OPT_ENUM.ENABLE, # ENABLE / MF_NO_INTERAC / DISABLE / AUTO
                 loggername = ' ⚡', 
                 addCustumLvl = False):

    useLogger = True if filename != False else False

    pc = profiler_collecteur()
    pc.options(interractivity = interractivity # ENABLE / MF_NO_INTERAC / DISABLE / AUTO
            , useLogger = useLogger
            , loggername = loggername
            , addCustumLvl = addCustumLvl
            , profilerlvl = 25)

    logger = logging.getLogger(loggername)

    if filename:
        logging.basicConfig(filename=filename, filemode='w')
    else :
        logging.basicConfig()

    @profiler
    def my_func():
        a = [1] * (10 ** 6)
        b = [2] * (2 * 10 ** 7)  
        time.sleep(2)
        del b
        time.sleep(2)
        return a

    a = my_func()
    if useLogger and filename!=None :
        if addCustumLvl :
            logger.profiler(pc.__str__())
        else :
            logger.info(pc.__str__())


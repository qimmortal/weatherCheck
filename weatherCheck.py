################################################################
#   This is a tool meant to retrieve current, forecast, and 7-day historical weather based on user input.
#       This tool uses the Weather Underground API, thanks to all the meteorologists!
#       www.wunderground.com
#
#       Additional thanks to Kevin and Q, thank you for your support and resources.  :-)
#
# Copyright 2015 Shaun Potts
################################################################

import requests
import json
import datetime
import getpass
from   datetime import date, timedelta
import sys
import argparse
import logging

#   Importing prettyPrint just for testing REMOVE ONCE FINISHED
import pprint
pp = pprint

#-----------------------------------------------------------------------
# Globals
#-----------------------------------------------------------------------
EXIT_STATUS_OK         = 0
EXIT_STATUS_ERROR      = 1
WEATHERCHECK_CURRTEMP  = None
WEATHERCHECK_ZIPCODE   = None
WEATHERCHECK_THREEDAYFORECAST  = None
WEATHERCHECK_AGOODDAY          = None
WEATHERCHECK_PASTWEEKAVG       = None
WEATHERCHECK_PASTWEEKDAILYAVG  = None
WEATHERCHECK_APIKEY            = '5f348904b60ca855'

VALID_WEATHERCHECK_OPTIONS = [
    WEATHERCHECK_CURRTEMP,
    WEATHERCHECK_ZIPCODE,
    WEATHERCHECK_THREEDAYFORECAST,
    WEATHERCHECK_AGOODDAY,
    WEATHERCHECK_PASTWEEKAVG,
    WEATHERCHECK_PASTWEEKDAILYAVG,
    WEATHERCHECK_APIKEY
    ]

# Getting date
thisDay = date.today()

#   Getting username
userName = getpass.getuser()

#   Number of days to pull down from Weather Underground (Cold have a CLI flag to change this)
days2GetHistoricals = 2

#   Setting up Weather Underground URL
wuUrl = 'http://api.wunderground.com/api/'

#   This is my API key, but could be swapped via CLI if we wanted another user
apiKey = '5f348904b60ca855/'

#   When looking for historicals this can be used for the URL
timeFrame = 'history_'

#   Static previous date to be replaced by CLI
desiredDate = '20150525'

#   Static preferred temp for "A good day to get out"
prefTemp = 70

#   Static preferred condition for "A good day to get out"
prefCond = 'Partly Cloudy'

#   Temporary location used for testing
#       NOTE: This can also be a zipcode '/q/94541.json' , I verified it pulled the same station KHWD
#               IF the zipcode can be verified it's no problem to run it.
locationQuery = '/q/CA/San Jose'

#   This var will allow for us to switch out data types from json if desired
urlExtension = '.json'

#   Temporary flag tossed for testing (Output should be human readable or json by request)
outputJson = False
outputAvgHist7DayTotal   = True
outputAvgHist7DayByDay   = False

outputcurrentTemp        = True
outputGoodDay            = True
outputThreeDayForecast   = True


###################################################################
#           TODO:
#                   -apiPoll: setup list or dict of lists capable arg for poaching more than a single value from returns
#
#                   -historyLookup: As requested, this script will deliver the *last 7 days' mean temp fro mSan Jose CA*
#                                    To be more useful and robust I should allow a user input for the date/zipcode for which to look passed.
#                                    ie; A user inputs 20140323 and gets mean temp data from between 20140316 20140322
#                                           Some provisions are in place that could allow these changes and would just take more time.   
#
#                   -A CACHE would be a good idea, be it in a temp dir, or a REDIS/et al database. Weather Underground's API call
#                       limit is easy to hit. (Not necessarily the 500/day, but the 10/min is easy as EACH day in the 7-day-call is singular)
#
#                   -Arg parsing, instead of test statements
#
#                   -Add arg to give city/state optionally vs zipcode as a creature-comfort
#
#                   -Actual logging and exception handling
###################################################################


#-----------------------------------------------------------------------------
def historyLookup(startDate, days2GoBack, wuKey, location):
    #   This def gathers historical data going back 'x' days from startDate
    
    #   Testing args to ensure we have what we need
    if not isinstance(startDate, date):
        print("Error: improper date format. Got %s of type %s" % startDate, type(startDate))
        sys.exit(1)
        
    if not isinstance(days2GoBack, int):
        print("Error: days2GoBack is expected to be a whole number. Got %s of type %s" % (days2GoBack, type(days2GoBack)))
        sys.exit(1)
        
    if not isinstance(wuKey, str):
        print("Error: wuKey (API key) is expected to be a string. Got: %s of type %s" % (wuKey, type(wuKey)))
        sys.exit(1)        
    
    if not isinstance(location, str):
        print("Error: location provided must be a string. Got: %s of type %s" % (location, type(location)))
        sys.exit(1)

    # Setting up counter which we'll use to start our lookup on the furthest days
    dateCountdown = days2GoBack
    
    # Creating an empty Dict to store each day's polled data
    histDict = dict()
    
    #   Looping through the date range to grab weather for the previous 7 days
    for i in range(1, (days2GoBack + 1)):
        #   Initializing meantempi holder
        pData = 0 
    
        #   setting timedelta each time we loop to grab another day
        d = startDate - timedelta(days=dateCountdown)
        assembledDate = '%s%s%s' % (d.year, d.strftime('%m'), d.strftime('%d'))
#        #   Adding this date's info to the dict
#        histDict.update({'%s%s%s' % (d.year, d.strftime('%m'), d.strftime('%d')) : 'Popped'})
    
        queryString = '%s%s%s%s%s%s' % (wuUrl, wuKey, timeFrame, assembledDate, location, urlExtension)

        
        #   Running the query to Weather Underground and pulling the mean temp
        pData = int(apiPoll(queryString)['history']['dailysummary'][0]['meantempi'])
        
        #   Adding this date's mean temp to the dir
        histDict.update({'%s' % assembledDate : pData})
        #   Decrementing our counter to poll the next date closer to startDate
        dateCountdown = dateCountdown - 1
        
        
    return histDict
    
#----------------------------------------------------------------    
def apiPoll(assembledQuery):
        #   TODO: Adjust this def to accept a list, or possibly a dict of things to pull from retrieved data
        #            instead of a full json dump

    #   This def assembles an http call for json data from Weather Underground
    #   We assume the wuUrl global var is the canonical source for the API's URL
    
    # Assuring the assembledQuery is a string
    if not isinstance(assembledQuery, str):
        print("Error: apiPoll must be given a string, got: %s of type %s" % (assembledQuery, type(assembledQuery)))

        sys.exit(1)
        
    print(assembledQuery)    
    r = requests.get(assembledQuery)
    data = r.json()

    #   Testing return to ensure that it doesn't contain an 'error' key. (The operation DOES NOT fail and responds with 200 anyway)
    if 'error' in data['response']:
        print("\n   Error retrieving weather: %s" % data['response']['error']['description'])
        sys.exit(1)

    return data        
    
    
#----------------------------------------------------------------

def lookAtHistory():
    #   This def handles historical requests from the user, 
    #       including 7-day overall meant temp of an area, per day, and a json holding the data

    if outputJson:
        lookupHist = historyLookup(thisDay, days2GetHistoricals, apiKey, locationQuery)
        return lookupHist
        
    elif outputAvgHist7DayTotal is True:
        lookupHist = historyLookup(thisDay, days2GetHistoricals, apiKey, locationQuery)
        weeklyAvg = sum(lookupHist.values()) / len(lookupHist.values())
        print("The average temperature of %s was %0d F over the last 7 days." % (locationQuery, weeklyAvg))
            
            
    elif outputAvgHist7DayByDay is True:
        lookupHist = historyLookup(thisDay, days2GetHistoricals, apiKey, locationQuery)
        print("\n  The average temperature for the last 7 days is as follows:\n")
        for key, value in lookupHist.items():
            print("Average Temperature for %s was %sF" % (key, value))
            
#----------------------------------------------------------------------------

def currentTemp(givenZip):
    #   This def pulls current weather data for a given zipcode
    
# http://api.wunderground.com/api/5f348904b60ca855/conditions/q/94541.json    
    lookupCurrQuery = "%s%sconditions/q/%s%s" % (wuUrl, apiKey, givenZip, urlExtension)
    
    #   Pulling current data from Weather Underground
    try: 
        currTemp = apiPoll(lookupCurrQuery)['current_observation']['temp_f']
        if not outputcurrentTemp:
            print("The current temperature is %0d F")
        
        #   Failing to get the current temp data should drop us out and tell us
    except:
        print("Error")
        sys.exit(1)

    return currTemp    
#----------------------------------------------------------------------------

def forecastWeather(givenZip):
    #   This def takes a user-input zipcode and a switch for either 3-day or "a good day to get out"
    #       (Future additions may include different preferences for "A good day to get out")
    
    # Making a legend of keys to ease the use of super-long lines ahead
    fC  = 'forecast'
    sFc = 'simpleforecast'
    fCd = 'forecastday'
    fH  = 'fahrenheit'
    hG  = 'high'
    cD  = 'conditions'
    wD  = 'weekday'
    mN  = 'monthname'
    
    lookupCurrQuery = "%s%sforecast/q/%s%s" % (wuUrl, apiKey, givenZip, urlExtension)
    
    #   Pulling forecast data from Weather Underground,... or.... the FUTURE!!
    try:
        theFuture = apiPoll(lookupCurrQuery)
        
        #Failing to get the forecast data should drop us out and tell us
    except:
        print("Error")
        sys.exit(1)

    #   If the good day flag was thrown check today's conditions and high temp    
    if outputGoodDay:
        try:
            # Checking forecastday 0 as that signifies "today" (1, 2, 3 are the 3day forecast)
            forecastTemp = int(theFuture[fC][sFc][fCd][0][hG][fH])
            forecastCond = theFuture[fC][sFc][fCd][0][cD]
            
            #   Ensuring both the high temp and the sunny conditions are both met then printing
            if (forecastTemp == prefTemp) and (forecastCond == prefCond):
                print("\n   Today will be a good day to get out of the house.")
                print("The forecast is %s with a high of %0d F" % (forecastCond, forecastTemp))
                
        except:
            print("Error")
            sys.exit(1)
            
        print(forecastTemp)
        print(forecastCond)    
            
        
    #   If the 3-day forecast flag is thrown return it
    if outputThreeDayForecast:
        try:
            threeDayDict = dict()
            print("\n   Three Day forecast for %s" % givenZip)
            
            for i in range(1, 4):
                #   Pushing each day into a seperate dict as storing them via weekday named keys causes sorting
                threeDayDict.update({'Day%s' % i : theFuture[fC][sFc][fCd][i]})
                
        except:        
            print("Error")
            raise
            sys.exit(1)

        if outputJson == True:
            return threeDayDict
            
        else:
            #   As a json output wasn't asked for, we are simply printing te 3day forecast to stdout
            for i in range(1, 4):
                print("The forecast for %s %s %s is %s with a high of %s F" % 
                (threeDayDict['Day%s' % i]['date'][wD], 
                 threeDayDict['Day%s' % i]['date'][mN], 
                 threeDayDict['Day%s' % i]['date']['day'], 
                 threeDayDict['Day%s' % i][cD], 
                 threeDayDict['Day%s' % i][hG][fH])
                )
        
        
                
#--------------------------------  Yay running stuff!  
# Main
#-----------------------------------------------------------
def main():

    try:
        # Setting up logger
     #   logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        
        #   Initialize arg parser
        parser = argparse.ArgumentParser(description="Process CLI args")
       
       
        #   Setting up valid CLI args
        parser.add_argument("--currenttemp",
                        help="Get the current temperature in Fahrenheit. (5-digit zipcode required)",
                        action="store_true", default=None)
                        
        #   Zip codes are the only args we take that aren't simply switch flags, process them properly.                
        parser.add_argument("--zipcode",
                        help="5-digit zip code for city you want weather info for. (last 7-days\' avg temp locked to San Jose)",
                        action="store",  default=None)
                        
        parser.add_argument("--threedayforecast",
                        help="Shows 3-day forecast for a given zipcode (5-digit zipcode required)",
                        action="store_true", default=None)
                        
        parser.add_argument("--agoodday",
                        help="Checks today's forecast to see if it will be both Sunny and exactly 68F",
                        action="store_true", default=None)
                        
        parser.add_argument("--pastweekavg",
                        help="Returns the passed 7 days\' average temperature as a total average",
                        action="store_true", default=None)
                        
        parser.add_argument("--pastweekdailyavg",
                        help="Different than \'pastweekavg\', this returns the passed 7 days\' average temps individually",
                        action="store_true", default=None)
                        
        parser.add_argument("--apikey",
                        help="Our great friends at Weather Underground require an api key to use their service, use yours, mine defaults just in case",
                        default='5f348904b60ca855')
        
        # Parse arguments
        args = parser.parse_args()
        #argsDict = vars(args)
        print(args.apikey)

        
        if not args:
            parser.error("No action specified. Please choose an action, such as: --currenttemp, --agoodday, --threedayforecast, --pastweekavg, or --pastweekdailyavg")
            print('crap')
        #   Ensuring that CLI args match available options: 
        if not args:
            parser.error("Invalid option specified. Please choose an action, such as: --currenttemp, --agoodday, --threedayforecast, --pastweekavg, or --pastweekdailyavg")
    
#        if WEATHERCHECK_PASTWEEK in args:
#            print("got here")
    
    
    # Catching argument errors:
    except:
        print("Error")
        raise
        return EXIT_STATUS_ERROR
        
    return EXIT_STATUS_OK
    
if __name__ == '__main__':
    exit_status = main()
    sys.exit(exit_status)
    
# main()    
    
########## TODO: argparsing instead of test statements
#forecastWeather(94541)

#currentTemp(94541)    
#lookAtHistory()
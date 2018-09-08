import datetime as dt

# start_dayOffTrade = 'Friday'
# start_timeOffTrade = '13:00'
# end_dayOffTrade = 'Friday'
# end_timeOffTrade = '23:38'

def convert_day(day_name):

    day_num = None

    if day_name == 'Monday':
        day_num = 0
    elif day_name == 'Tuesday':
        day_num = 1
    elif day_name == 'Wednesday':
        day_num = 2
    elif day_name == 'Thursday':
        day_num = 3
    elif day_name == 'Friday':
        day_num = 4
    elif day_name == 'Saturday':
        day_num = 5
    elif day_name == 'Sunday':
        day_num = 6

    return day_num

def chk_OffTrade(start_dayOffTrade, start_timeOffTrade, end_dayOffTrade, end_timeOffTrade ):

    #convert day name to day number
    startDay = convert_day(start_dayOffTrade)

    #to tackle Monday issue
    temp_endDay = convert_day(end_dayOffTrade)
    if temp_endDay < startDay:
        endDay = temp_endDay + 7
    else:
        endDay = temp_endDay

    if startDay == None or endDay == None:
        return True

    # get setting start time
    startTime = start_timeOffTrade.split(':')
    startHour = int(float(startTime[0]))
    startMinute = int(float(startTime[1]))

    #get setting end time
    endTime = end_timeOffTrade.split(':')
    endHour = int(float(endTime[0]))
    endMinute = int(float(endTime[1]))

    # get current date and time
    day = dt.datetime.today().weekday()
    hour = dt.datetime.now().hour
    minute = dt.datetime.now().minute

    
#    print(day, hour, minute)
#    print(startDay, startHour, startMinute)
#    print(endDay, endHour, endMinute)
    
    
    offTrade = False

    if day > startDay:
        if day < endDay:
            offTrade = True
        elif day == endDay and hour < endHour:
            offTrade = True
        elif day == endDay and hour == endHour and minute <= endMinute:
            offTrade = True

    elif day == startDay and hour > startHour:
        if day < endDay:
            offTrade = True
        elif day == endDay and hour < endHour:
            offTrade = True
        elif day == endDay and hour == endHour and minute <= endMinute:
            offTrade = True

    elif day == startTime and hour == startHour and minute >= startMinute:
        if day < endDay:
            offTrade = True
        elif day == endDay and hour < endHour:
            offTrade = True
        elif day == endDay and hour == endHour and minute <= endMinute:
            offTrade = True
            
    # to address Monday = 0 issue
    elif day == 0:
        if hour < endHour:
            offTrade = True            
        if hour == endHour and minute <= endMinute:
            offTrade = True
        

    return offTrade
    
# filter NO TRADE time
#start_day = 'Saturday'
#start_time = '3:00'
#end_day = 'Monday'
#end_time = '6:15'
#
#
#print ('OFF Trade =',chk_OffTrade(start_day, start_time, end_day, end_time))





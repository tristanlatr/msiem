# -*- coding: utf-8 -*-
"""
    msiem query
"""
import json
import time
from .session import ESMSession
from .exceptions import ESMException
from .utils import log, getTimes
from .constants import (POSSIBLE_TIME_RANGE,
    POSSIBLE_FIELD_TYPES, 
    POSSIBLE_OPERATORS, 
    POSSIBLE_VALUE_TYPES,
    POSSIBLE_ALARM_STATUS,
    POSSBILE_ROW_ORDER,
    DEFAULTS_EVENT_FIELDS)

class QueryBase(ESMSession):
    def __init__(self, time_range=None, start_time=None, end_time=None):
        super().__init__()

        #Declaring attributes
        self._time_range=str()
        self._start_time=str()
        self._end_time=str()
        
        #init attributes
        if time_range and time_range is not 'CUSTOM':
            self.time_range=time_range

        elif start_time and end_time :
            self.time_range='CUSTOM'
            self.start_time=start_time
            self.end_time=end_time

        else :
            raise ESMException("The query must have valid time specifications. Please refer to documentation.")

    @property
    def time_range(self):
        return self._time_range

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    @time_range.setter
    def time_range(self, time_range):
        """
        Set the time range of the query to the specified string value. Default : LAST_3_DAYS
        """

        try:
            if time_range in POSSIBLE_TIME_RANGE :
                self._time_range=time_range
                
            else:
                raise ESMException("The time range must be in "+str(POSSIBLE_TIME_RANGE))

        except:raise
    
    @start_time.setter
    def start_time(self, start_time):
        """
        Set the time start of the query. Time range must be CUSTOM for this to work.
        """
        try:
            if start_time is not None :
                if self._time_range == 'CUSTOM':
                    self._start_time=start_time
                    
                else:
                    raise ESMException("The time range must be 'CUSTOM' if you want to specify a custom start time")
            else:
                self._start_time=None
                
        except:raise
    
    @end_time.setter
    def end_time(self, end_time):
        """
        Set the time end of the query. Time range must be CUSTOM for this to work.
        """
        try:
            if end_time is not None :
                if self._time_range == 'CUSTOM':
                    self._end_time=end_time
                   
                else:
                    raise ESMException("The time range must be 'CUSTOM' if you want to specify a custom end time")
            else :
                self._end_time=None
                
        except:raise

    def execute(self):
        raise ESMException("Base query can't be executed.")

class AlarmQuery(QueryBase):

    def __init__(self, status='', page_size=5000, page_number=1, filters=None, **args):

        """
        filters : [(field, [values]), (field, [values])]
        field can be an EsmTriggeredAlarm field, EsmTriggeredAlarmDetail or an EsmTriggeredAlarmEvent field
        """

        super().__init__(**args)

        #Declaring attributes
        self._status=str()
        self._page_size=int()
        self._page_number=int()

        self._filters = list(tuple())

        #Setting attributes
        self.status=status
        self.page_size=page_size
        self.page_number=page_number

    @property
    def status(self):
        return self._status

    @property
    def page_size(self):
        return self._page_size

    @property
    def page_number(self):
        return self._page_number

    @status.setter
    def status(self, status):
        """
        Set the status filter of the alarm query. 'acknowledged', 'unacknowledged', '' or null -> all (default is '')
        """
        try:
            if type(status) is str : 
                if status.lower() in POSSIBLE_ALARM_STATUS :
                    self._status=status
                    
                else:
                    raise ESMException("Illegal value of status filter. The status must be in "+str(POSSIBLE_ALARM_STATUS))

        except:raise
    
    @page_size.setter
    def page_size(self, page_size):
        """
        Set the page size, the number of alarms to return per page (default is 5000, max is 5000).
        """
        try:
            if page_size > 0 and page_size <= 5000 :
                self._page_size=page_size
                
            else:
                raise ESMException("The page size must be in 0-5000")

        except:raise

    @page_number.setter
    def page_number(self, page_number):
        """
        Set the page number. Which page of alarms we want to return (default is 1)
        """
        self._page_number=page_number
        
    def execute(self):
        """"
        Execute the query.
        Returns a list of Alarms.
        """

        resp=None
        if self.time_range is 'CUSTOM' :
            resp=self.esmRequest(
                'get_alarms_custom_time',
                time_range=self.time_range,
                start_time=self.start_time,
                end_time=self.end_time,
                status=self.status,
                page_size=self.page_size,
                page_number=self.page_number
                )

        else :
            resp=self.esmRequest(
                'get_alarms',
                time_range=self.time_range,
                status=self.status,
                page_size=self.page_size,
                page_number=self.page_number
                )
            

        alarms=list()
        for alarm_data in resp :
            alarm = Alarm(**alarm_data)
            alarms.append(alarm)

        return alarms

class Alarm(ESMSession):
    """
    Alarm object. 
    Gives possibility to access alarm fields and related events.
    Delete, Ack, or Unack alarm.
    """

    def __init__(self, **args):
        
        self.id = {"value" : 0}
        self.summary = ''
        self.assignee = ''
        self.severity = 0
        self.triggeredDate = ''
        self.acknowledgedDate = ''
        self.acknowledgedUsername = ''
        self.alarmName = ''
        self.conditionType = 0

        self.__dict__.update(args)

        self._detailed = None

        try :
            if self.id['value'] == 0:
                raise ESMException("The id of the alarm haven't been initialized ! Make sure you pass a dict object with a 'value' field as the id.")
        except KeyError :
            raise KeyError("Make sure you pass a dict object with a 'value' field as the id.")
        except ESMException:
            raise
        
        super().__init__()

    @property
    def detailed(self):
        if self._detailed is None :
            self._detailed = DetailedAlarm(self)
        return self._detailed

    @property
    def events(self):
        return self.detailed.events

    def delele(self):
        self.esmRequest('delete_alarms', ids=[self.id])
        return
    
    def acknowledge(self):
        self.esmRequest('ack_alarms', ids=[self.id])
        return

    def unacknowledge(self):
        self.esmRequest('unack_alarms', ids=[self.id])
        return  

class DetailedAlarm(Alarm):
    """
    Alarm details object. Based on EsmTriggeredAlarmDetail
    """
    def __init__(self, alarm):
        
        """
        self.id = {"value" : 0} #duplicate
        self.summary = '' #duplicate
        self.assignee = '' #duplicate
        self.severity = 0 #duplicate
        self.triggeredDate  = '' #duplicate
        self.acknowledgedDate  = ''#duplicate
        self.acknowledgedUsername  = ''#duplicate
        self.alarmName  = ''#duplicate
        self.conditionType  = 0 #duplicate
        """

        super().__init__(id=alarm.id)
        
        """
        self.filters  = ''
        self.queryId = 0
        self.alretRateMin = 0
        self.alertRateCount = 0
        self.percentAbove = 0
        self.percentBelow = 0
        self.offsetMinutes = 0
        self.timeFilter  = ''
        self.maximumConditionTriggerFrequency = 0
        self.useWatchlist = ''
        self.matchField = ''
        self.matchValue = ''
        self.healthMonStatus = ''
        self.assigneeId = 0
        self.escalatedDate = ''
        self.caseId = 0
        self.caseName = ''
        self.iocName = 0
        self.iocId = 0
        self.description = ''
        self.actions = ''
        """

        self._events = list()

        resp = self.esmRequest('get_alarm_details', id=alarm.id)
        
        #self.__dict__.update(resp)

        self._events = resp['events']

    @property
    def detailed(self):
        return self

    @property
    def events(self):
        return self._events

class Event(ESMSession):
    """ Based on EsmTriggeredAlarmEvent """
    def __init__(self, **args):
        self.fields=dict().update(**args)

class EventQuery(QueryBase):
    """
    Interface to qryExecuteDetail?type=EVENT method.
    """

    #Declaring static value
    _possible_fields = None

    def __init__(self, fields=None, filters=None, 
        limit=5000, offset=0, order=None, compute_time_range=True, **args):
        """
       
        fields list of string, need to convert that into list of {
            "name": "(name)",
            "typeBits": 0,
            "id": "(id)"
            }

        order tuple (direction, field) to list of {
            "direction": "ASCENDING or DESCENDING",
            "field": {
                "name": ""
                }
            }

        filters 
            1 / list of {
                (field , [values]) #easy mode
            }

            2 / list of QueryFilter
        """

        self._compute_time_range = compute_time_range
        
        super().__init__(**args)\

        #Singleton attribute mapping
        self._possible_fields = EventQuery._possible_fields

        #Constant
        self._type='EVENT'
        self._groupType='NO_GROUP'

        if self._possible_fields is None :
            self._possible_fields = self.esmRequest('get_possible_fields', type=self._type, groupType=self._groupType)

        #Declaring attributes
        self._fields=set()
        self._filters=list()

        self._limit=int()
        self._offset=int()

        self._reverse=bool()

        self._order=[{
            "direction": None,
            "field": {
                "name": None
                }
            }]

        self.fields = DEFAULTS_EVENT_FIELDS
        self.fields = fields

        self.filters = filters

        self.order = order
        
        self._limit = limit
        self._offset = offset

        self._query = None

        self._executed = False

    @property
    def fields(self):
        return([{'name':value} for value in list(self._fields)])

    @property
    def filters(self):
        return([f.configDict() for f in self._filters])

    @property
    def limit(self):
        return(self._limit)

    @property
    def offset(self):
        return(self._offset)

    @property
    def reverse(self):
        return(self._reverse)

    @property
    def order(self) :       
        return(self._order)

    @property
    def time_range(self):
        return(super().time_range)

    @order.setter
    def order(self, order):
        #tuple (direction, field)
        #TODO check valid value
        if type(order) is tuple :
            self._order[0]['direction']=order[0]
            self._order[0]['field']['name']=order[1]

    @filters.setter
    def filters(self, filters):
        for values in filters :
            self.add_filter(values)

    def add_filter(self, fil):
        if type(fil) is tuple :
            self._filters.append(FieldFilter(*fil))

        elif isinstance(fil, QueryFilter) :
            self._filters.append(fil)
        
        else :
            raise ESMException("Sorry the filters must be either a tuple(fiels, [values]) or a QueryFilter sub class.")

    @fields.setter
    def fields(self, fields):
        if fields :
            for f in fields :
                if f :
                    self.add_field(f) 

    def add_field(self, field):
        try:
            if any(f.get('name', None) == field for f in self._possible_fields):
                self._fields.add(field)
            else:
                raise ESMException("Illegal value for the value "+field+". The field must be in "+ str([f['name'] for f in self._possible_fields]))
        except GeneratorExit :
            pass
        except:raise

    @time_range.setter
    def time_range(self, time_range):
        """
        Set the time range of the query to the specified string value.
        """
        if time_range is not 'CUSTOM' and self._compute_time_range :
            try :
                times = getTimes(time_range)
                self._time_range='CUSTOM'
                self._start_time=times[0]
                self._end_time=times[1]

            except ESMException :
                log.warning('The choosen time range is not fully supported. This mean that only the first page of events will be returned. '+str(ESMException))
                self._time_range=time_range
        else :
            self._time_range=time_range
  

    def execute(self):
        """"
            Execute the query.
            Returns a list of Events.
        """

        if self.time_range is 'CUSTOM' :
            self._query=self.esmRequest(
                'event_query_custom_time',
                asynch=False,

                time_range=self.time_range,
                start_time=self.start_time,
                end_time=self.end_time,
                #order=self.order, TODO support order
                fields=self.fields,
                filters=self.filters,
                limit=self.limit,
                offset=self.offset,
                includeTotal=False
                )

        else :
            self._query=self.esmRequest(
                'event_query',
                asynch=False,

                time_range=self.time_range,
                #order=self.order, TODO support order
                fields=self.fields,
                filters=self.filters,
                limit=self.limit,
                offset=self.offset,
                includeTotal=False
                )
        
        log.debug("EsmRunningQuery object : "+str(self._query))

        if self._waitFor(self._query['resultID']):
            self._executed = True

        return (self.getEvents())

    def _waitFor(self, resultID):
        log.debug("Waiting for the query to be executed on the SIEM...")
        while True:
            status = self.esmRequest('query_status', resultID=resultID)
            if status : 
                if status['complete'] is True :
                    return True
                else :
                    time.sleep(0.5)
            else :
                raise ESMException("There was an error while waiting for the query to execute.")

    def getEvents(self, startPos=0, numRows=None):
        if self._executed :
            if not numRows :
                numRows=self.limit
                
            result=self.esmRequest('query_result', startPos=startPos, numRows=numRows, resultID=self._query['resultID'])
            events=self._parseResult(result['columns'], result['rows'])
            return events
        else :
            raise ESMException("Query need to be executed before to be able to get events.")

    def _parseResult(self, columns, rows):
        events=list()
        for row in rows :
            event=dict()
            for i in range(len(columns)-1):
                event.update({columns[i]['name']:row['values'][i]})
            events.append(event)
        return events

class QueryFilter(ESMSession):

    _possible_filters = None

    def __init__(self):
        super().__init__()

        #Mapping singleton attributes
        self.__possible_filters = QueryFilter._possible_filters

        #Setting up static constant
        if self._possible_filters is None :
            self._possible_filters = self._get_possible_filters()

    def _get_possible_filters(self):
        return(self.esmRequest('get_possible_filters'))

    def configDict(self):
        return 'TODO'

class GroupFilter(QueryFilter):
    """
        Based on EsmFilterGroup
    """
    def __init__(self, *filters, logic='AND'):
        super().__init__()

        #Declaring attributes
        self._filters=filters
        self._logic=logic

    def configDict(self):
        return({
            "type": "EsmFilterGroup",
            "filters": [f.configDict() for f in self._filters],
            "logic":self._logic
            })
        
class FieldFilter(QueryFilter):
    """
    Based on EsmFieldFilter
    """

    def __init__(self, name, values, operator='IN'):
        super().__init__()

        #Declaring attributes
        self._name=str()
        self._operator=str()
        self._values=list()

        self._name = name
        self.operator = operator
        self.values = values

    def configDict(self):
        return ({
            "type": "EsmFieldFilter",
            "field": {"name": self._name},
            "operator": self._operator,
            "values": self._values
            })

    @property
    def field_name(self):
        return (self._field_name)
    
    @property
    def operator(self):
        return (self._operator)

    @property
    def values(self):
        return (self._values)

    @field_name.setter
    def field_name(self, name):
        try:
            if any(f.get('name', None) == name for f in self._possible_filters):
                self._field_name = name
            else:
                raise ESMException("Illegal value for the "+name+" field. The filter must be in :"+str([f['name'] for f in self._possible_filters]))
        except GeneratorExit:
            pass
        except:
            raise

    @operator.setter
    def operator(self, operator):
        try:
            if operator in POSSIBLE_OPERATORS :
                self._operator = operator
            else:
                raise ESMException("Illegal value for the filter operator "+operator+". The operator must be in "+str(POSSIBLE_OPERATORS))
        except:
            raise
        
    def add_value(self, type, **args):
        """
        Please refer to the EsmFilterValue documentation
        """
        try:
            type_template=None
            for possible_value_type in POSSIBLE_VALUE_TYPES :
                if possible_value_type['type'] == type :
                    type_template=possible_value_type
                    break

            if type_template is not None :
                if type_template['key'] in args :
                    self._values.append({'type':type, type_template['key']:args[type_template['key']]})

                else:
                    raise ESMException("You must provide a valid named parameter containing the value(s). The key must be in "+str(POSSIBLE_VALUE_TYPES))

            else:
                raise ESMException("Illegal value type for the value filter. The type must be in "+str(POSSIBLE_VALUE_TYPES))
        except:
            raise

    def add_basic_value(self, value):
        self.add_value(type='EsmBasicValue', value=value)

    @values.setter
    def values(self, values):
        for v in values :
            if type(v) is dict :
                self.add_value(**v)

            elif type(v) is str :
                self.add_basic_value(v)




import sys
import os
from datetime import date
import requests
from html.parser import HTMLParser
from google.cloud import firestore
from flask import escape

db = firestore.Client(project=os.environ.get('GOOGLE_CLOUD_PROJECT'))
sections_ref = db.collection(u'sections')

class ScheduleParser(HTMLParser):
    def __init__(self,semester,coll_ref):
        HTMLParser.__init__(self)
        self.incell = False
        self.row = []
        self.cellcontents = ""
        self.semester = semester
        self.sectionCount = 0
        self.coll_ref = coll_ref

    def getSectionCount(self):
        return self.sectionCount

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        if tag == "td":
            self.incell = True
            self.cellcontents = ""


    def handle_data(self, data):
        if self.incell:
            if ( len(self.cellcontents) == 0 ):
                self.cellcontents = data
            else:
                self.cellcontents += " " + data

class RSParser(ScheduleParser):
    def __init__(self,semester,coll_ref):
        ScheduleParser.__init__(self,semester,coll_ref)

    def handle_endtag(self, tag):
        if tag == "td":
            self.row.append( self.cellcontents.strip() )
            self.incell = False
        if tag == "tr":
            if len( self.row ) == 19 and len( self.row[4] ) != 0 and self.row[1] != 'Cancel':
                if self.row[18] == '':
                    self.row[18] = 'instructor TBD'
                self.coll_ref.add(
                    {
                        'sectionId': self.semester+self.row[4],
                        'crn': self.row[4],
                        'subj': self.row[5],
                        'crse': self.row[6],
                        'sec': self.row[7],
                        'title': self.row[9].replace( chr(160), ' '),
                        'instructor': self.row[18].replace( chr(160), ' '),
                        'semester': self.semester
                    }
                )
                self.sectionCount = self.sectionCount + 1


class CSParser(ScheduleParser):
    def __init__(self,semester,coll_ref):
        ScheduleParser.__init__(self,semester,coll_ref)

    def handle_endtag(self, tag):
        if tag == "td":
            self.row.append( self.cellcontents.strip() )
            self.incell = False
        if tag == "tr":
            if len( self.row ) == 12 and len( self.row[1] ) != 0 and self.row[1] != 'CRN':
                if self.row[11] == '':
                    self.row[11] = 'instructor TBD'
                self.coll_ref.add(
                    {
                        'sectionId': self.semester+self.row[1],
                        'crn': self.row[1],
                        'subj': self.row[2],
                        'crse': self.row[3],
                        'sec': 'CS',
                        'title': self.row[5].replace( chr(160), ' '),
                        'instructor': self.row[11].replace( chr(160), ' '),
                        'semester': self.semester
                    }
                )                    
                self.sectionCount = self.sectionCount + 1

def loadRS(semester,coll_ref):
    payload2 = { 'term_in': semester,
                 'sel_subj': ['dummy', '%'],
                 'sel_day': 'dummy',
                 'sel_schd': ['dummy', '%'],
                 'sel_insm': ['dummy', '%'],
                 'sel_camp': 'dummy',
                 'sel_levl': 'dummy',
                 'sel_sess': 'dummy',
                 'sel_instr': 'dummy',
                 'sel_ptrm': ['dummy', '%'],
                 'sel_attr': 'dummy',
                 'sel_dept': ['dummy', '%'],
                 'sel_crse': '',
                 'sel_title': '%',
                 'begin_hh': '0',
                 'begin_mi': '0',
                 'begin_ap': 'a',
                 'end_hh': '0',
                 'end_mi': '0',
                 'end_ap': 'a',
                 'sel_incl_restr': 'Y',
                 'sel_incl_preq': 'Y',
                 'SUB_BTN': 'GET+Courses' }

    r2 = requests.post( 'https://swing.langara.bc.ca/prod/hzgkfcls.P_GetCrse', data=payload2, verify=True )

    parser = RSParser(semester,coll_ref)
    parser.feed( r2.text )
    return parser.getSectionCount()

def loadCS(semester,coll_ref):
    payload2 = { 'term_in': semester,
                 'sel_pgm': '',
                 'sel_subj': ['dummy', '%'],
                 'sel_day': 'dummy',
                 'sel_schd': 'dummy',
                 'sel_insm': 'dummy',
                 'sel_camp': 'dummy',
                 'sel_levl': 'dummy',
                 'sel_sess': 'dummy',
                 'sel_instr': 'dummy',
                 'sel_ptrm': 'dummy',
                 'sel_attr': 'dummy',
                 'sel_dept': ['dummy', '%'],
                 'sel_crse': '',
                 'sel_title': '%',
                 'begin_hh': '0',
                 'begin_mi': '0',
                 'begin_ap': 'a',
                 'end_hh': '0',
                 'end_mi': '0',
                 'end_ap': 'a',
                 'SUB_BTN': 'GET+Courses' }

    r2 = requests.post( 'https://swing.langara.bc.ca/prod/hzgkfcls.P_GetCrse', data=payload2, verify=True )

    parser = CSParser(semester,coll_ref)
    parser.feed( r2.text )
    return parser.getSectionCount()

def delete_colletion( coll_ref, batch_size ):
    docs = coll_ref.limit( batch_size ).stream()
    deleted = 0

    for doc in docs:
        doc.reference.delete()
        deleted = deleted + 1 
    
    if deleted >= batch_size:
        return delete_colletion( coll_ref, batch_size )


def emptyAndUpdateSections():
    delete_colletion( sections_ref, 100 )
    today = date.today()
    year1 = today.year
    semester1 = ((today.month-1)//4 + 1)*10
    if semester1 == 30:
        year2 = year1 + 1
        semester2 = 10
    else:
        year2 = year1
        semester2 = semester1 + 10

    rssemester1 = '{}{}'.format(year1,semester1)
    rssemester2 = '{}{}'.format(year2,semester2)
    cssemester1 = '0{}{}'.format(year1,semester1//10)
    cssemester2 = '0{}{}'.format(year2,semester2//10)

    rsSectionCount = loadRS( rssemester1, sections_ref )
    csSectionCount = loadCS( cssemester1, sections_ref )
    rsSectionCount = rsSectionCount + loadRS( rssemester2, sections_ref )
    csSectionCount = csSectionCount + loadCS( cssemester2, sections_ref )
    return { 'rsSectionCount': rsSectionCount, 'csSectionCount': csSectionCount }

def sections(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    rssemester = ''
    cssemester = ''

    request_json = request.get_json(silent=True)
    request_args = request.args

    if request_json:
        if 'rssemester' in request_json:
            rssemester = request_json['rssemester']
        if 'cssemester' in request_json:
            cssemester = request_json['cssemester']
    elif request_args:
        if 'rssemester' in request_args:
            rssemester = request_args['rssemester']
        if 'cssemester' in request_args:
            cssemester = request_args['cssemester']

    rssemester = rssemester.strip()
    cssemester = cssemester.strip()

    rssemester = rssemester[:6]
    cssemester = cssemester[:6]


    docs = sections_ref.where(u'semester', u'in', [rssemester,cssemester]).stream()
    results = []
    for doc in docs:
        results.append( doc.to_dict() )

    return {'Items': results}
        


def updateSections(event, context):
    """Background Cloud Function to be triggered by Pub/Sub.
    Args:
         event (dict):  The dictionary with data specific to this type of
                        event. The `@type` field maps to
                         `type.googleapis.com/google.pubsub.v1.PubsubMessage`.
                        The `data` field maps to the PubsubMessage data
                        in a base64-encoded string. The `attributes` field maps
                        to the PubsubMessage attributes if any is present.
         context (google.cloud.functions.Context): Metadata of triggering event
                        including `event_id` which maps to the PubsubMessage
                        messageId, `timestamp` which maps to the PubsubMessage
                        publishTime, `event_type` which maps to
                        `google.pubsub.topic.publish`, and `resource` which is
                        a dictionary that describes the service API endpoint
                        pubsub.googleapis.com, the triggering topic's name, and
                        the triggering event type
                        `type.googleapis.com/google.pubsub.v1.PubsubMessage`.
    Returns:
        None. The output is written to Cloud Logging.
    """
    import base64

    print("""This Function was triggered by messageId {} published at {} to {}
    """.format(context.event_id, context.timestamp, context.resource["name"]))

    if 'data' in event:
        name = base64.b64decode(event['data']).decode('utf-8')
    else:
        name = 'World'

    emptyAndUpdateSections()

    print('Hello {}!'.format(name))


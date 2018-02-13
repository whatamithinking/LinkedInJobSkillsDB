
import requests,json
from tqdm import tqdm
from user_agent import generate_navigator
from bs4 import BeautifulSoup
from lxml import html
from _Config import *
import csv
from time import sleep
from _LinkedInJobSkillsDBConfig import *
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from queue import Queue
from threading import Thread
from random import uniform, randint

class LinkedInJobSkills():

    def __init__( self, Username=None, Password=None ):
        super( __class__, self ).__init__()
        self.Username = Username
        self.Password = Password
        self.Session = requests.session()
        self.SessionLoggedIn = False
        self.MinSleepSecs = 5
        self.MaxSleepSecs = 10
        self.DB = self.getDBSession()

    @staticmethod
    def getDBSession():
        '''
        Purpose:	Create a DB session and return.
        '''
        Engine = create_engine( DBPath )
        Base.metadata.bind = Engine
        DBSession = sessionmaker( bind=Engine )
        return DBSession()

    def _getLinksList( self, FilePath='SkillPageLinks.txt', StoreFilePath='SkillPageLinks.txt' ):
        '''
        Purpose: 	Get the skill page links either by crawling the LinkedIn directory index pages
                    or by loading from a file.
        Arguments:
            FilePath - str - [ optional ] path to the file where the skill page links are kept
                                By default, an attempt will be made to load the links from the default file path.
                                If None, the LinkedIn website will be scraped for the links.
            StoreFilePath - str - [ optional ]Path to the file where you will store the scraped skill page links.
                                    If None, any scraping results will not be stored in a file.
        Returns:
            SkillPageLinks - list of str - list of skill page links
        '''

        # LOAD FROM FILE IS POSSIBLE
        if FilePath != None:
            with open( FilePath, 'r' ) as SkillPageLinksFile:
                Reader = csv.reader( SkillPageLinksFile, delimiter=',' )
                SkillPageLinks = [ Row[ 0 ] for Row in Reader if len( Row ) > 0 ]
                return SkillPageLinks

        if not self.SessionLoggedIn: self._loginSession()

        SkillsBasePage = self.Session.get( \
            SITE[ 'Skills' ][ 'Base' ]
            ,headers=generate_navigator()
        )
        sleep(uniform(self.MinSleepSecs,self.MaxSleepSecs))
        SkillBaseXML = html.fromstring( SkillsBasePage.text )

        # COLLECT ALL TOPIC NAMES
        TopicNameElms = SkillBaseXML.xpath( '//ol[@class="bucket-list"]/li/a' )
        TopicNames = [ ( TopicNameElm.text.lower(), TopicNameElm.attrib[ 'href' ] ) \
                        for TopicNameElm in TopicNameElms ]
        ProgressBar = tqdm(total=len( TopicNames ), desc='Finding Skill Page Links', unit='Topic')
        SkillPageLinks = []

        for TopicName, TopicLink in TopicNames:

            # SPECIAL CASE FOR #
            if TopicName == '#': TopicName = 'more'

            # GET COUNT OF NUMBER OF SKILL PARENT PAGES FOR THIS TOPIC
            TopicPage = self.Session.get(
                TopicLink
                ,headers=generate_navigator()
            )
            TopicPageXML = html.fromstring( TopicPage.text )
            TopicPageElms = TopicPageXML.xpath( '//div[@class="section last"]/div/ul/li/a' )

            # GET THE URLS FOR THE PARENT PAGES OF SKILLS PAGES
            SkillParentPageLinks = []
            for iTopic in range( 1, len( TopicPageElms ) + 1 ):
                if 'topics-' in TopicPageElms[ iTopic - 1 ].attrib[ 'href' ]:											# if this is still a parent in dex page
                    SkillParentPageLink = SITE[ 'Skills' ][ 'Base' ][ :-1 ] + \
                                           SITE[ 'Skills' ][ 'TopicLinks' ]
                    SkillParentPageLink = SkillParentPageLink.format( TopicName=TopicName, TopicIndex=iTopic )
                else:																					# if this is a base skill page
                    SkillParentPageLink = TopicPageElms[ iTopic - 1 ].attrib[ 'href' ]
                SkillParentPageLinks.append(SkillParentPageLink)

            # VISIT EACH SKILL PARENT INDEX PAGE AND GET ALL OF THE URLS
            for SkillParentPageLink in SkillParentPageLinks:
                if 'topics-' in SkillParentPageLink:										# when topics are three layers deep
                    SkillParentPage = self.Session.get(
                        SkillParentPageLink
                        ,headers=generate_navigator()
                    )
                    sleep(uniform(self.MinSleepSecs, self.MaxSleepSecs))
                    SkillParentPageXML = html.fromstring( SkillParentPage.text )
                    SkillPageElms = SkillParentPageXML.xpath( '//div[@class="section last"]/div/ul/li/a' )
                    SkillPageLinks += [ SkillPageElm.attrib[ 'href' ] for SkillPageElm in SkillPageElms ]
                else:																		# some topics are only two layers deep
                    SkillPageLinks.append( SkillParentPageLink )

            ProgressBar.update( 1 )

        # SAVE ALL SKILL PAGE LINKS TO FILE AS CSV
        if StoreFilePath != None:
            with open( StoreFilePath, 'w') as SkillPageLinksFile:
                Writer = csv.writer( SkillPageLinksFile )
                SkillPageLinksArray = [ [ x ] for x in SkillPageLinks if not x in ( '', None ) ]
                Writer.writerows( SkillPageLinksArray )

        return SkillPageLinks

    def _getPublicIdentifier(self, LoginResultPage):
        '''
        Purpose:	Get the Public Identifier of the user, which is used
                    for locating their profile page.
        Arguments:
            LoginResultPage - str - the html page after loggin in. Feed page.
        Returns:
            PublicIdentifier - str - public identifier of the user
        '''
        LoginPageSoup = BeautifulSoup(LoginResultPage, 'lxml')
        PublicIdentifier = None
        for x in LoginPageSoup.findAll('code'):
            CodeContents = x.contents[0]
            if 'publicContactInfo' in CodeContents:
                UserInfoDictList = json.loads(CodeContents)
                for UserInfoDict in UserInfoDictList['included']:
                    if 'publicIdentifier' in UserInfoDict:
                        PublicIdentifier = UserInfoDict['publicIdentifier']
                        break
            if PublicIdentifier != None: break
        return PublicIdentifier

    def _loginSession(self, Username=None, Password=None):
        '''
        Purpose:	Login to this website using the provided credentials.
                    Uses requests, not webdriver. Login for requests only,
                    which cannot apply to jobs, but operates much faster than selenium.
        Arguments:
            Username - str - email address / username for site
            Password - str - password for your account with this site
        Returns:
            LoginSuccessful - bool - True if login was successful; False otherwise
        '''
        if self.SessionLoggedIn: return True
        if Username != None: self.Username = Username
        if Password != None: self.Password = Password
        if self.Password == None or self.Username == None:
            raise ValueError('ERROR : LOGIN CREDENTIALS REQUIRED')

        # SAVE THE SECURITY INFO
        LoginPage = self.Session.get(SITE['Login']['Base'])
        LoginPageSoup = BeautifulSoup(LoginPage.text, 'lxml')
        LoginPayload = SITE['Login']['Payload']
        for SecurityParam in SITE['Login']['Security']:
            SecurityValue = \
                LoginPageSoup.find('input', {'name': SecurityParam})['value']
            LoginPayload.update({SecurityParam: SecurityValue})

        # FILL OUT USERNAME AND PASSWORD
        LoginPayload.update({'session_key': self.Username
                                , 'session_password': self.Password})

        # SEND LOGIN REQUEST
        LoginHeaders = \
            generate_navigator().update(
                {
                    'X-IsAJAXForm': '1'
                    , 'save-data': 'on'
                    , 'referer'	: SITE[ 'Login' ][ 'Base' ]
                }
            )
        LoginResultPage = self.Session.post(
            SITE[ 'Login-Submit' ] ,data=LoginPayload
            ,headers=LoginHeaders
        )

        # CHECK IF LOGIN SUCCESSFUL
        if LoginResultPage.status_code != 200:
            LoginSuccessful = False
        else:
            LoginSuccessful = True
            self.PublicIdentifier = self._getPublicIdentifier( LoginResultPage.text )
        self.SessionLoggedIn = LoginSuccessful

        return LoginSuccessful

    def scrapeSkill( self, SkillPageLink, SkillPage=None ):
        '''
        Purpose:	Go to the skill page and scrape the list of companies and related skills with
                    counts representing how many times the link has been seen in the wild of LinkedIn.
        Arguments:
            SkillPageLink - str - url to the skill page
            SkillPage - requests page obj - [ optional ] the skill webpage to process
        Returns:
            SkillsDict - dict - dictionary of scraped skills data.
                                ex:
                                {
                                    'Companies' : [ ( 'Company A', 200 ), ( 'Company B', 900 ),...  ]
                                    ,'RelatedSkills' : [ ( 'Skill A', 200 ), ( 'Skill B', 900 ),...  ]
                                }
        '''

        if not self.SessionLoggedIn: self._loginSession()
        SkillsDict = {'Companies': [], 'RelatedSkills': []}
        if SkillPage == None:
            SkillPage = self.Session.get(
                SkillPageLink
                , headers=generate_navigator()
            )
        if SkillPage.status_code == 200:

            SkillPageXML = html.fromstring( SkillPage.text )
            try:
                Skill = SkillPageXML.xpath( '//h1[@class="page-title"]/text()' )[ 0 ]							# extract skill name from page
                SkillsDict.update( { 'Skill' : Skill } )
            except:
                print( 'No Skill Title Found : ' + str( SkillPageLink ) )

            # GET COMPANY & RELATION COUNT COMBOS
            try:
                CompanySkillStrings = \
                    SkillPageXML.xpath('//div[@class="stats-text-container"]/h3[contains(text(),"companies")]/..')[ 0 ].xpath(
                        './*/li/text()')
                for CompanySkillString in CompanySkillStrings:
                    Company, RelationCount = [ x.strip() for x in CompanySkillString.rsplit( '-', 1 ) ]
                    SkillsDict[ 'Companies' ].append( ( Company, RelationCount ) )
            except:
                print( 'No Company Skill Data : ' + str( SkillPageLink ) )

            # GET RELATED SKILLS
            try:
                RelatedSkillStrings = \
                    SkillPageXML.xpath('//div[@class="stats-text-container"]/h3[contains(text(),"skills")]/..')[ 0 ].xpath(
                        './*/li/text()')
                for RelatedSkillString in RelatedSkillStrings:
                    RelatedSkillValue, RelationCount = [ x.strip() for x in RelatedSkillString.rsplit( '-', 1 ) ]
                    SkillsDict[ 'RelatedSkills' ].append( (RelatedSkillValue, RelationCount) )
            except:
                print( 'No Related Skill Data : ' + str( SkillPageLink ) )

        return SkillsDict

    def refreshSkill( self, SkillPageLink, SkillsDict=None ):
        '''
        Purpose:	Request the skill link page and scrape all info for that skill and update
                    in the skills database.
        Arguments:
            SkillPageLink - str - url to the skill page
            SkillDict - dict - [ optional ] dictionary of skill data. if not included,
                                the webpage will be requested to get the data.
        Returns:
            True/False - bool - True if refresh successful. False otherwise.
        '''
        if not self.SessionLoggedIn: self._loginSession()
        if SkillsDict == None: SkillsDict = self.scrapeSkill( SkillPageLink )
        DB = self.getDBSession()

        # IF THIS IS AN EMPTY SKILL PAGE, JUST RECORD THE LINK, SO WE DO NOT COME BACK HERE AGAIN AND WASTE TIME
        if not 'Skill' in SkillsDict:

            # UPDATE SKILL
            SkillRow = DB.query(RootSkill).filter_by(link=SkillPageLink).first()

            # IF ROW EXISTS, UPDATE WITH NEW COUNT
            if SkillRow != None:
                SkillRow.timestamp = datetime.utcnow()
                DB.commit()

            # IF ROW DOES NOT EXIST, INSERT NEW COMPANY SKILL
            else:
                NewRootSkill = RootSkill( link=SkillPageLink
                                          ,timestamp=datetime.utcnow())
                DB.add( NewRootSkill )
                DB.flush()
                DB.commit()

        # IF THIS IS A POPULATED PAGE, INSERT DATA TO DB
        else:

            Skill = SkillsDict[ 'Skill' ]

            # UPDATE SKILL
            SkillRow = DB.query(RootSkill).filter_by( skill=Skill ).first()

            # IF ROW EXISTS, UPDATE WITH NEW COUNT
            if SkillRow != None:
                SkillRow.link = SkillPageLink
                SkillRow.timestamp = datetime.utcnow()
                DB.commit()

            # IF ROW DOES NOT EXIST, INSERT NEW COMPANY SKILL
            else:
                NewRootSkill = RootSkill( 	skill=Skill
                                            ,link=SkillPageLink
                                            ,timestamp=datetime.utcnow())
                DB.add( NewRootSkill )
                DB.flush()
                DB.commit()

            # FILL IN COMPANIES IN DB
            if 'Companies' in SkillsDict:
                for Company, RelationCount in SkillsDict[ 'Companies' ]:

                    # CHECK IF COMPANY SKILL EXISTS
                    CompanySkillRow = DB.query( CompanySkill ).filter_by( 	skill=Skill
                                                                                ,company=Company ).first()

                    # IF ROW EXISTS, UPDATE WITH NEW COUNT
                    if CompanySkillRow != None:
                        CompanySkillRow.relation_count = RelationCount
                        CompanySkillRow.timestamp = datetime.utcnow()
                        DB.commit()

                    # IF ROW DOES NOT EXIST, INSERT NEW COMPANY SKILL
                    else:
                        NewCompanySkill = CompanySkill( skill=Skill
                                                        ,company=Company
                                                        ,relation_count=RelationCount
                                                        ,timestamp=datetime.utcnow())
                        DB.add( NewCompanySkill )
                        DB.flush()
                        DB.commit()

            # FILL IN RELATED SKILLS IN DB
            if 'RelatedSkills' in SkillsDict:
                for RelatedSkillValue, RelationCount in SkillsDict[ 'RelatedSkills' ]:

                    # CHECK IF SKILL / RELATED SKILL COMBO EXISTS
                    RelatedSkillRow = DB.query( RelatedSkill ).filter_by( 	skill=Skill
                                                                                ,related_skill=RelatedSkillValue ).first()

                    # IF ROW EXISTS, UPDATE WITH NEW COUNT
                    if RelatedSkillRow != None:
                        RelatedSkillRow.relation_count = RelationCount
                        DB.commit()

                    # IF ROW DOES NOT EXIST, INSERT NEW COMPANY SKILL
                    else:
                        NewRelatedSkill = RelatedSkill( skill=Skill
                                                        ,related_skill=RelatedSkillValue
                                                        ,relation_count=RelationCount
                                                        , timestamp=datetime.utcnow())
                        DB.add( NewRelatedSkill )
                        DB.flush()
                        DB.commit()

        DB.close()
        return True

    def refreshAllSkills( self, ProcessingWorkerCount=3, SkipExisting=False ):
        '''
        Purpose:	Refresh all of the skill page links data in the database.
        Arguments:
            ProcessingWorkerCount - int - the number of workers for processing the webpages
                                                and putting them in the database
            SkipExisting - bool - True, then skip over links already in the database.
                                    False, scrape all skill pages, regardless of presence in db
        Returns:
            Nothing
        '''

        if not self.SessionLoggedIn: self._loginSession()

        SkillPageQueue = Queue()
        SkillPageLinkList = []
        SkillThreads = []

        # STARTUP WORKER TO GET THE PAGES AND DUMP THEM TO A QUEUE
        SkillPageLinks = l._getLinksList()
        SkillPageLinkList = SkillPageLinks

        # DO NOT REFRESH LINKS ALREADY IN DB IF OPTION SELECTED
        if SkipExisting:
            DB = self.getDBSession()
            AlreadyFoundSkillsRows = DB.execute( 'select link from root_skills' )
            AlreadyFoundLinks = [ x[ 'link' ] for x in AlreadyFoundSkillsRows ]
            SkillPageLinkList = [ x for x in SkillPageLinkList \
                                  if not x in AlreadyFoundLinks ]
        
        SkillPageCount = len( SkillPageLinkList )
        def getSkillPage( InputList, OutputQueue ):
            ProgressBar = tqdm( total=SkillPageCount, desc='Getting Skill Pages', unit='Skill Page' )
            while True:
                RandomLinkIndex = randint( 0, len( SkillPageLinkList ) )
                SkillPageLink = InputList[ RandomLinkIndex ]            # pick a random list item
                InputList.pop( RandomLinkIndex )                        # remove used link from list
                if SkillPageLink == None: break
                SkillPage = self.Session.get(						    # get the page and pass to next method
                    SkillPageLink
                    , headers=generate_navigator()
                )
                if SkillPage.status_code == 999:
                    print( 'YOU ARE BEING BLOCKED | ATTEMTING RECONNECT...' )
                    self.Session.close()                                # try opening up a new session
                    sleep(uniform(self.MinSleepSecs + self.MaxSleepSecs, \
                                  self.MaxSleepSecs * 2) )
                    self.Session = requests.session()
                    self._loginSession()
                    SkillPage = self.Session.get(                       # get the page and pass to next method
                        SkillPageLink
                        , headers=generate_navigator()
                    )
                    if SkillPage.status_code == 999: 
                        print( 'RECONNECTION FAILED : GIVING UP' )
                        break
                    else:
                        print( 'RECONNECTION SUCCEEDED : CONTINUING' )
                OutputQueue.put( ( SkillPage, SkillPageLink ) )		    # put results in the output queue
                ProgressBar.update( 1 )
                sleep(uniform(self.MinSleepSecs, self.MaxSleepSecs) )   # sleep for being a polite bot
        GetSkillPageThread = Thread( target=getSkillPage
                                     ,args=( SkillPageLinkList, SkillPageQueue ) )
        GetSkillPageThread.daemon = True
        GetSkillPageThread.start()
        SkillThreads.append( GetSkillPageThread )

        # STARTUP THE SKILL PAGE PROCESSOR WORKER
        def processSkillPage( InputQueue ):
            while True:
                SkillTuple = InputQueue.get()
                if SkillTuple == None:
                    break
                SkillPage, SkillPageLink = SkillTuple
                SkillsDict = self.scrapeSkill( SkillPageLink, SkillPage )
                self.refreshSkill( SkillPageLink, SkillsDict )
                InputQueue.task_done()
        for i in range( ProcessingWorkerCount ):                    # run workers to process pages gotten
            SkillProcessor = Thread( target=processSkillPage
                                        ,args=( SkillPageQueue, ) )
            SkillProcessor.daemon = True
            SkillProcessor.start()
            SkillThreads.append( SkillProcessor )

        while len( SkillPageLinkList ) != 0:                        # wait for all pages to be gotten
            sleep( 1 )
        SkillPageQueue.join()										# wait for all skill pages to be read and saved to db
        for i in range( len( SkillThreads ) ):						# stop the workers
            SkillPageQueue.put( None )
        for t in SkillThreads:										# wait for all threads to stop
            t.join()














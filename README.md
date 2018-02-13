# LinkedIn Job Skills DB

Database of job skills scraped from the LinkedIn skills directory. Stored in an SQLAlchemy database.

## Features

* Partially-complete job skills database scraped from LinkedIn
* Refresh job skills in database
* Scrape job skills pages
* Automatic login to LinkedIn

###### Notes

Tested with Python 3.4.8

## Getting Started

1. Download the code and unzip

2. Open the folder and open command prompt to that directory.

3. Install requirements from the requirements.txt file:
    ```
    pip install -r requirements.txt
    ```
    
4. Run the following code in command prompt:
    ```
    from LinkedInJobSkills import LinkedInJobSkills
    l=LinkedInJobSkills( 'YOUR_EMAIL@example.com','YOUR_LINKEDIN_PASSWORD' )
    ```
    
5. Start querying your skills database:
    ```
    Skill = 'python'
    RootSkillRows = l.DB.execute( 'select * from root_skills where skill = {Skill}'.format( Skill=Skill ) )
    ...
    # do what you want with data
    ....
    ```

#### Notes

##### Database Design

* companies - id, timestamp, skill, company, relation_count
* related_skills - id, timestamp, skill, related_skill, relation_count
* root_skills - id, timestamp, skill, link

###### Notes

* relation_count = number of times a relationship between a skill and a company or a skill and another skill was observed
* timestamp = last time the skill was updated
* root_skills = stores the links to skills pages and keeps track of skill pages visited which had data and which did not have data ( skill is null )

##### Refresh Skills Data

* Set your min and max sleep times, which will be normally distributed to make the requests look more human and to be polite to their servers.
    ```
    l.MinSleepSecs = 5                                  # min amount of time between requests
    l.MaxSleepSecs = 10                                 # max amount of time between requests
    ```
* To refresh just one skill's data:
    ```
    Skill = 'python'
    SkillPageLinks = l._getLinksList()                  # get list of all skill page links. Last updated: 02/11/2018
    FilteredSkillPageLinks = \
        [ x for x in SkillPageLinks if Skill in x ]     # filter to get links for this skill
    for SkillPageLink in FilteredSkillPageLinks:        # refresh data for each skill page
        l.refreshSkill( SkillPageLink )
    ```
* To refresh the entire skills database:
    ```
    l.refreshAllSkills( SkipExisting=True )             # scrape the entire skills directory and repopulate database
    ```

## Authors

* **Connor Mawynes** - *Initial work*


# LinkedInJobSkillsDB

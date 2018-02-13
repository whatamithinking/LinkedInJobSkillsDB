
'''
Purpose:	Provide configuration settings for this specific website.
			These settings may be subject to change over time, which is 
			up the website.
'''

SITE = {
	'Login' 		: {
		'Base'		: 'https://www.linkedin.com/uas/login'			# from the address bar
		,'Security'	: {												# security is always added to the payload for the page
			'loginCsrfParam' 	: ''
			,'sourceAlias'		: ''
		}
		,'Payload'	: {
			'session_key' 		: ''
			,'session_password' : ''
			,'isJSEnabled'		: 'false'
		}
	}
	,'Login-Submit'	: 'https://www.linkedin.com/uas/login-submit'	# from the network traffic
	,'Skills'		: {
		'Base'			: "https://www.linkedin.com/directory/topics/"
		,'TopicLinks'	: '-{TopicName}-{TopicIndex}/'	
	}
}
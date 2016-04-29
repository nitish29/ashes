from urllib.request import Request, urlopen
import urllib.parse
import json
from django.shortcuts import render
from django.conf import settings
import pdb
from .models import PlayerStats, UserPlayers, PlayerMatchData
from operator import itemgetter
from django.http import HttpResponseRedirect, HttpResponse
from datetime import datetime
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import math


def home(request):
	try:
		errors = []
		
		recommendations = playerRecommendation()
		#print(recommendations)

		players = PlayerStats.objects.all()
		userPlayers = UserPlayers.objects.all()
		#pdb.set_trace()
		caa_player_performace_dict = {}
		bif_player_performace_dict = {}

		for individual_player in userPlayers:
			player_match_data = []
			player_caa_string = ''
			player_bif_string = ''
			player_match_data = PlayerMatchData.objects.values('player_name', 'caa', 'last_bat_impact').filter(player_name=individual_player.player_name.player_name).order_by('match_date')
			for individual_match_data in player_match_data:
				player_caa_string = str(player_caa_string) + str(individual_match_data['caa']) + ', '
				player_bif_string = str(player_bif_string) + str(individual_match_data['last_bat_impact']) + ', '
			#print(player_caa_string)
			#print(player_bif_string)
			player_caa_string = player_caa_string[:-2]
			player_bif_string = player_bif_string[:-2]
			# caa_integer_list = [float(x) for x in player_caa_string.split(',')]
			caa_player_performace_dict[individual_player.player_name.player_name] = player_caa_string
			bif_player_performace_dict[individual_player.player_name.player_name] = player_bif_string
		#print(caa_player_performace_dict)
		#pdb.set_trace()
		postive_weekly_sentiment_dict, negative_weekly_sentiment_dict, neutral_weekly_sentiment_dict = makeSolrCallForSentimentsInRange("sentiments_for_all")

		#date_range_str = '2016-03-18,' + '2016-03-22,' + '2016-03-26,' + '2016-03-30,' + '2016-04-03'
		date_range_str = '2016-04-12,' + '2016-04-16,' + '2016-04-20,' + '2016-04-24,' + '2016-04-29'

		context = {'allPlayerList': players, 'myPlayerList': userPlayers, 'caa_dict': caa_player_performace_dict, 'bif_dict': bif_player_performace_dict, 'positive_weekly': postive_weekly_sentiment_dict, 'negative_weekly': negative_weekly_sentiment_dict, 'neutral_weekly': neutral_weekly_sentiment_dict, 'date_range': date_range_str, 'recommendations': recommendations}

	except:
		
		errors.append('Error Completing request')
		context = {'errors': errors}

	return render(request, "playercompare.html", context)


def playerRecommendation():
	userPlayers = UserPlayers.objects.all()
	allPlayers = PlayerMatchData.objects.all()

	player_name_list = []
	my_player_list = []
	other_player_list = []

	for my_player in userPlayers:
		player_name = my_player.player_name.player_name
		 #player_dict = { my_player_data['player_name'] : my_player_data['caa']}
		player_name_list.append(player_name)

	for individual_player in allPlayers:
		single_player_data = PlayerMatchData.objects.values('player_name', 'caa', 'last_bat_impact', 'match_date').filter(player_name=individual_player.player_name.player_name).order_by('-match_date')[0]

		if single_player_data['player_name'] in player_name_list and single_player_data not in my_player_list:
			my_player_list.append(single_player_data)
		elif single_player_data not in other_player_list and single_player_data not in my_player_list:
			other_player_list.append(single_player_data)

	sorted_my_player_list_caa = ascSortPlayerList(my_player_list, 'caa')
	print(sorted_my_player_list_caa)
	sorted_my_player_list_bif = ascSortPlayerList(my_player_list, 'last_bat_impact')
	sorted_other_player_list_caa = sortPlayerList(other_player_list, 'caa')
	sorted_other_player_list_bif = sortPlayerList(other_player_list, 'last_bat_impact')

	# pdb.set_trace()
	drop_player1 = sorted_my_player_list_caa[0]
	drop_player2 = sorted_my_player_list_caa[1]
	drop_player3 = sorted_my_player_list_bif[0]

	pick_player1 = sorted_other_player_list_caa[0]
	pick_player2 = sorted_other_player_list_caa[1]
	pick_player3 = sorted_other_player_list_bif[0]

	return {'drop_player1': drop_player1, 'drop_player2': drop_player2, 'drop_player3': drop_player3, 'pick_player1': pick_player1, 
	'pick_player2': pick_player2, 'pick_player3': pick_player3}


def playerPage(request):
		try:
			errors = []
			userPlayers = UserPlayers.objects.all()

			if request.method == 'GET' and 'myPlayerSelect' in request.GET:			
				my_player = UserPlayers.objects.get(player_name=request.GET['myPlayerSelect'])
				player_wise_articles = makeSolrCall(my_player.articles_search_target, 'articles')
				player_wise_tweets = makeSolrCall(my_player.search_target, 'playerTweets')
				player_news_channel_tweets = makeSolrCall(my_player.search_target, 'newsTweets')

				#pdb.set_trace()

				print(player_wise_articles['response']['docs'])
				print ('Type///////////////////////')
				print(type(player_wise_articles['response']['docs']))
				print ('Articles Count Check ??????????')
				print(len(player_wise_articles['response']['docs']))
				
				player_match_data = []

				for player_match_record in PlayerMatchData.objects.filter(player_name=request.GET['myPlayerSelect']):
					player_match_data.append(player_match_record)
				print("printing all rows....")
				print(player_match_data)

				# timeline sentiment analysis for single player
				player_sentiment_dict = makeSolrCallForSinglePlayerSentiment(my_player)

				#pagination for articles

				if(len(player_wise_articles['response']['docs']) != 0):	
					article_list=player_wise_articles['response']['docs']
					paginator=Paginator(article_list, 3)
					article_page=request.GET.get('article_page')
					if article_page:
						print('request.GET.get(article_page) empty !!!')
					else:
						article_page=2
					articles=paginator.page(article_page)

				#pagination for user tweets
				if(len(player_wise_tweets['response']['docs']) != 0):	
					user_tweet_list = player_wise_tweets['response']['docs']
					paginator = Paginator(user_tweet_list, 3)
					user_tweet_page = request.GET.get('user_tweet_page')
					if user_tweet_page:
						print('request.GET.get(user_tweet_page) empty !!!')
					else:
						user_tweet_page = 2
					user_tweets = paginator.page(user_tweet_page)

				#pagination for news tweets
				if(len(player_news_channel_tweets['response']['docs']) != 0):	
					news_tweet_list = player_news_channel_tweets['response']['docs']
					paginator = Paginator(news_tweet_list, 4)
					news_tweet_page = request.GET.get('news_tweet_page')
					if news_tweet_page:
						print('request.GET.get(news_tweet_page) empty !!!')
					else:
						news_tweet_page = 2
					news_tweets = paginator.page(news_tweet_page)

				context = {'myPlayerList': userPlayers, 'articles': articles, 'myPlayer': my_player,
				'playerTweets': user_tweets, 'newsTweets': news_tweets, 'match_data': player_match_data, 'player_sentiment_dict': player_sentiment_dict}
			else:
				context = {'myPlayerList': userPlayers}

		except:
			errors.append('Error Completing request')
			context = {'errors': errors}

		return render(request, "player.html", context)


def playerCompareAction(request):
	try:
		errors = []
		#pdb.set_trace()
		players = PlayerStats.objects.all()
		userPlayers = UserPlayers.objects.all()

		recommendations = playerRecommendation()

		caa_player_performace_dict = {}
		bif_player_performace_dict = {}

		for individual_player in userPlayers:
			player_match_data = []
			player_caa_string = ''
			player_bif_string = ''
			player_match_data = PlayerMatchData.objects.values('player_name', 'caa', 'last_bat_impact').filter(player_name=individual_player.player_name.player_name).order_by('match_date')
			for individual_match_data in player_match_data:
				player_caa_string = str(player_caa_string) + str(individual_match_data['caa']) + ', '
				player_bif_string = str(player_bif_string) + str(individual_match_data['last_bat_impact']) + ', '
			#print(player_caa_string)
			#print(player_bif_string)
			player_caa_string = player_caa_string[:-2]
			player_bif_string = player_bif_string[:-2]
			# caa_integer_list = [float(x) for x in player_caa_string.split(',')]
			caa_player_performace_dict[individual_player.player_name.player_name] = player_caa_string
			bif_player_performace_dict[individual_player.player_name.player_name] = player_bif_string
		#print(caa_player_performace_dict)

		postive_weekly_sentiment_dict, negative_weekly_sentiment_dict, neutral_weekly_sentiment_dict = makeSolrCallForSentimentsInRange("sentiments_for_all")

		#date_range_str = '2016-03-18,' + '2016-03-22,' + '2016-03-26,' + '2016-03-30,' + '2016-04-03'
		date_range_str = '2016-04-12,' + '2016-04-16,' + '2016-04-20,' + '2016-04-24,' + '2016-04-29'

		if request.GET['myPlayerSelect']:
			#pdb.set_trace()
			my_selected_player = request.GET['myPlayerSelect']
			my_player = PlayerMatchData.objects.filter(player_name=my_selected_player).order_by('-match_date')
			if my_player:
				my_player = my_player[0]
			else:
				message = 'Oops! ' + my_selected_player + ' didnt play in this week. Please select another player.'
				print(message)
				context = {'allPlayerList': players, 'myPlayerList': userPlayers, 'message': message, 'caa_dict': caa_player_performace_dict, 'bif_dict': bif_player_performace_dict, 'positive_weekly': postive_weekly_sentiment_dict, 'negative_weekly': negative_weekly_sentiment_dict, 'neutral_weekly': neutral_weekly_sentiment_dict, 'date_range': date_range_str, 'recommendations': recommendations}
				return render(request, "playercompare.html", context)
		
		if request.GET['allPlayerSelect']:

			other_selected_player = request.GET['allPlayerSelect']
			other_player = PlayerMatchData.objects.filter(player_name=other_selected_player).order_by('-match_date')
			if other_player:
				other_player = other_player[0]
			else:
				message = 'Oops! ' + other_selected_player + ' didnt play in this week. Please select another player.'
				print(message)
				context = {'allPlayerList': players, 'myPlayerList': userPlayers, 'message': message, 'caa_dict': caa_player_performace_dict, 'bif_dict': bif_player_performace_dict, 'positive_weekly': postive_weekly_sentiment_dict, 'negative_weekly': negative_weekly_sentiment_dict, 'neutral_weekly': neutral_weekly_sentiment_dict, 'date_range': date_range_str, 'recommendations': recommendations}
				return render(request, "playercompare.html", context)

		my_player_caa = my_player.caa
		other_player_caa = other_player.caa

		if my_player_caa > other_player_caa:
			message = 'We recommend ' + my_player.player_name.player_name + ' over ' + other_player.player_name.player_name
			print(message)
		else:
			message = 'We recommend ' + other_player.player_name.player_name + ' over ' + my_player.player_name.player_name
			print(message)

		context = {'allPlayerList': players, 'myPlayerList': userPlayers, 'myPlayer': my_player, 'otherPlayer': other_player, 'message': message, 'caa_dict': caa_player_performace_dict, 'bif_dict': bif_player_performace_dict, 'positive_weekly': postive_weekly_sentiment_dict, 'negative_weekly': negative_weekly_sentiment_dict, 'neutral_weekly': neutral_weekly_sentiment_dict, 'date_range': date_range_str, 'recommendations': recommendations}

	except:
		errors.append('Error Completing request')
		context = {'errors': errors}

	return render(request, "playercompare.html", context)


def makeSolrCallForSinglePlayerSentiment(individual_player):

	#date_range_wt20 = ['date:[2016-03-15T00:00:00Z TO 2016-03-18T00:00:00Z]', 'date:[2016-03-19T00:00:00Z TO 2016-03-22T00:00:00Z]', 'date:[2016-03-23T00:00:00Z TO 2016-03-26T00:00:00Z]', 'date:[2016-03-27T00:00:00Z TO 2016-03-30T00:00:00Z]', 'date:[2016-03-31T00:00:00Z TO 2016-04-03T00:00:00Z]']
	date_range_wt20 = ['date:[2016-04-09T00:00:00Z TO 2016-04-12T00:00:00Z]','date:[2016-04-13T00:00:00Z TO 2016-04-16T00:00:00Z]','date:[2016-04-17T00:00:00Z TO 2016-04-20T00:00:00Z]','date:[2016-04-21T00:00:00Z TO 2016-04-24T00:00:00Z]','date:[2016-04-25T00:00:00Z TO 2016-04-29T00:00:00Z]']
	
	player_weekly_sentiment_dict = {}
	playerSearchTarget = individual_player.search_target

	weekly_positive_string = ''
	weekly_negative_string = ''
	weekly_neutral_string = ''
		
	for individual_dates in date_range_wt20:
		
		request_params = urllib.parse.urlencode(
			{'q': '*' + playerSearchTarget + '*', 'wt': 'json', 'indent': 'true', 'rows': 1000, 'start': 0, 'defType': 'dismax', 'qf': 'search_target', 'fl': 'targeted_sentiment', 'fq': individual_dates})
		request_params = request_params.encode('utf-8')
		req = urllib.request.urlopen(settings.SOLR_BASEURL_TWEET,
									 request_params)

		content = req.read()
		decoded_json_content = json.loads(content.decode())

		weekly_records_player = decoded_json_content['response']['numFound']
		count_neutral = 0
		count_positive = 0
		count_negative = 0

		for individual_sentiments in decoded_json_content['response']['docs']:
			if (individual_sentiments['targeted_sentiment'] == 'neutral'):
				count_neutral = count_neutral + 1
			elif (individual_sentiments['targeted_sentiment'] == 'positive'):
				count_positive = count_positive + 1
			else:
				count_negative = count_negative + 1
		weekly_positive_percentage = round((float(count_positive) / float(weekly_records_player)) * 100, 2)
		weekly_negative_percentage = round((float(count_negative) / float(weekly_records_player)) * 100, 2)
		weekly_neutral_percentage = round((float(count_neutral) / float(weekly_records_player)) * 100, 2)

		weekly_positive_string = str(weekly_positive_string) + str(weekly_positive_percentage) + ', '
		weekly_negative_string = str(weekly_negative_string) + str(weekly_negative_percentage) + ', '
		weekly_neutral_string = str(weekly_neutral_string) + str(weekly_neutral_percentage) + ', '

	weekly_positive_string = weekly_positive_string[:-2]
	weekly_negative_string = weekly_negative_string[:-2]
	weekly_neutral_string = weekly_neutral_string[:-2]

	player_weekly_sentiment_dict['Positive %'] = weekly_positive_string
	player_weekly_sentiment_dict['Negative %'] = weekly_negative_string
	player_weekly_sentiment_dict['Neutral %'] = weekly_neutral_string

	return player_weekly_sentiment_dict


def makeSolrCallForSentimentsInRange(queryType):
	
	#curl --globoff 'http://localhost:8983/solr/cricketTweetsCore/select?&wt=json&q=*kohli*&defType=dismax&qf=keywords+entity+text&indent=true&start=0&rows=100&bq=date^20+retweets^10+favorites^5&sort=date+desc,retweets+desc,favorites+desc&fq=date:[2016-03-25T00:00:00Z%20TO%202016-04-03T00:00:00Z]'
	#pdb.set_trace()
	myPlayers = UserPlayers.objects.all()

	# date_range_wt20 = ['date:[2016-03-15T00:00:00Z TO 2016-03-18T00:00:00Z]','date:[2016-03-19T00:00:00Z TO 2016-03-22T00:00:00Z]','date:[2016-03-23T00:00:00Z TO 2016-03-26T00:00:00Z]','date:[2016-03-27T00:00:00Z TO 2016-03-30T00:00:00Z]','date:[2016-03-31T00:00:00Z TO 2016-04-03T00:00:00Z]']

	date_range_wt20 = ['date:[2016-04-09T00:00:00Z TO 2016-04-12T00:00:00Z]','date:[2016-04-13T00:00:00Z TO 2016-04-16T00:00:00Z]','date:[2016-04-17T00:00:00Z TO 2016-04-20T00:00:00Z]','date:[2016-04-21T00:00:00Z TO 2016-04-24T00:00:00Z]','date:[2016-04-25T00:00:00Z TO 2016-04-29T00:00:00Z]']

	postive_weekly_sentiment_dict = {}
	negative_weekly_sentiment_dict = {}
	neutral_weekly_sentiment_dict = {}

	#pdb.set_trace()
	
	for individual_player in myPlayers:
		playerName = individual_player.player_name.player_name
		playerSearchTarget = individual_player.search_target

		weekly_positive_string = ''
		weekly_negative_string = ''
		weekly_neutral_string = ''

		if queryType == "sentiments_for_all":
			
			for individual_dates in date_range_wt20:
				
				request_params = urllib.parse.urlencode(
					{'q': '*'+playerSearchTarget+'*', 'wt': 'json', 'indent': 'true', 'rows': 1000, 'start': 0, 'defType': 'dismax','qf': 'search_target','fl':'targeted_sentiment', 'fq': individual_dates})
				request_params = request_params.encode('utf-8')
				req = urllib.request.urlopen(settings.SOLR_BASEURL_TWEET,
											 request_params)

				content = req.read()
				decoded_json_content = json.loads(content.decode())

				weekly_records_player = decoded_json_content['response']['numFound']
				
				count_neutral = 0
				count_positive = 0
				count_negative = 0

				for individual_sentiments in decoded_json_content['response']['docs']:
					if (individual_sentiments['targeted_sentiment'] == 'neutral'):
						count_neutral = count_neutral + 1
					elif (individual_sentiments['targeted_sentiment'] == 'positive'):
						count_positive = count_positive + 1
					else:
						count_negative = count_negative + 1
				weekly_positive_percentage = round((float(count_positive) / float(10)) * 100, 2)
				weekly_negative_percentage = round((float(count_negative) / float(10)) * 100, 2)
				weekly_neutral_percentage = round((float(count_neutral) / float(10)) * 100, 2)

				weekly_positive_string = str(weekly_positive_string) + str(weekly_positive_percentage) + ', '
				weekly_negative_string = str(weekly_negative_string) + str(weekly_negative_percentage) + ', '
				weekly_neutral_string = str(weekly_neutral_string) + str(weekly_neutral_percentage) + ', '

			weekly_positive_string = weekly_positive_string[:-2]
			weekly_negative_string = weekly_negative_string[:-2]
			weekly_neutral_string = weekly_neutral_string[:-2]

			postive_weekly_sentiment_dict[playerName] = weekly_positive_string
			negative_weekly_sentiment_dict[playerName] = weekly_negative_string
			neutral_weekly_sentiment_dict[playerName] = weekly_neutral_string
		
	return postive_weekly_sentiment_dict, negative_weekly_sentiment_dict, neutral_weekly_sentiment_dict


def makeSolrCall(search_query, queryType):
	
	#curl --globoff 'http://localhost:8983/solr/cricketTweetsCore/select?&wt=json&q=*kohli*&defType=dismax&qf=keywords+entity+text&indent=true&start=0&rows=100&bq=date^20+retweets^10+favorites^5&sort=date+desc,retweets+desc,favorites+desc&fq=date:[2016-03-25T00:00:00Z%20TO%202016-04-03T00:00:00Z]'

	if queryType == "tweet":
		request_params = urllib.parse.urlencode(
			{'q': '*' + search_query + '*', 'wt': 'json', 'indent': 'true', 'rows': 1000, 'start': 0, 'defType': 'dismax', 'qf': 'search_target', 'fl': 'targeted_sentiment'})
		request_params = request_params.encode('utf-8')
		req = urllib.request.urlopen(settings.SOLR_BASEURL_TWEET,
									 request_params)
	elif queryType == "articles":
		#pdb.set_trace()
		request_params = urllib.parse.urlencode(
			{'q': '*' + search_query + '*', 'wt': 'json', 'indent': 'true', 'rows': 500, 'start': 0, 'defType': 'dismax', 'qf': 'title keywords summary content', 'fl': 'title,article_url,date,summary', 'bq': 'title^20 summary^10 date^5 ', 'sort': 'date desc'})
		request_params = request_params.encode('utf-8')
		req = urllib.request.urlopen(settings.SOLR_BASEURL_ARTICLES,
									 request_params)
	elif queryType == "playerTweets":
		#pdb.set_trace()
		request_params = urllib.parse.urlencode(
			{'q': '*' + search_query + '*', 'wt': 'json', 'indent': 'true', 'rows': 500, 'start': 0, 'defType': 'dismax', 'qf': 'keywords entity text', 'bq': 'date^20 retweets^10 favorites^5', 'sort': 'date desc,retweets desc,favorites desc', 'fq': '-username:(ICC,ESPNcricinfo,cricbuzz,CricketNDTV)'})
		request_params = request_params.encode('utf-8')
		req = urllib.request.urlopen(settings.SOLR_BASEURL_TWEET,
									 request_params)
	elif queryType == "newsTweets":
		#pdb.set_trace()
		request_params = urllib.parse.urlencode(
			{'q': '*' + search_query + '*', 'wt': 'json', 'indent': 'true', 'rows': 500, 'start': 0, 'defType': 'dismax', 'qf': 'keywords entity text', 'bq': 'date^20 retweets^10 favorites^5', 'sort': 'date desc,retweets desc,favorites desc', 'fq': 'username:(ICC,ESPNcricinfo,cricbuzz,CricketNDTV)'})
		request_params = request_params.encode('utf-8')
		req = urllib.request.urlopen(settings.SOLR_BASEURL_TWEET,
									 request_params)

	content = req.read()
	decoded_json_content = json.loads(content.decode())
	return decoded_json_content


def getIndividualPlayerSentiment(UserPlayers):
	#player_list = []
	playerName = UserPlayers.player_name.player_name
	playerSearchTarget = UserPlayers.search_target
	player_sentiment_result = makeSolrCall(playerSearchTarget, 'tweet')

	total_records_player = player_sentiment_result['response']['numFound']
	#print(total_records_player)
	count_neutral = 0
	count_positive = 0
	count_negative = 0
	for individual_sentiments in player_sentiment_result['response']['docs']:
		if (individual_sentiments['targeted_sentiment'] == 'neutral'):
			count_neutral = count_neutral + 1
		elif (individual_sentiments['targeted_sentiment'] == 'positive'):
			count_positive = count_positive + 1
		else:
			count_negative = count_negative + 1
	positive_percentage = (float(count_positive) / float(total_records_player)) * 100
	negative_percentage = (float(count_negative) / float(total_records_player)) * 100
	neutral_percentage = (float(count_neutral) / float(total_records_player)) * 100

	player_dict = {'player_name': playerName, 'positive_tweet_count': count_positive, 'negative_tweet_count': count_negative, 'neutral_tweet_count': count_neutral, 'total_count': total_records_player, 'positive_percentage': positive_percentage, 'negative_percentage': negative_percentage, 'neutral_percentage': neutral_percentage}
	# player_list.append(player_dict)

	return player_dict


def getPlayerSentimentList(UserPlayers):

	player_list = []

	for individual_player in UserPlayers:
			playerName = individual_player.player_name.player_name
			playerSearchTarget = individual_player.search_target
			player_sentiment_result = makeSolrCall(playerSearchTarget, 'tweet')

			total_records_player = player_sentiment_result['response']['numFound']
			#print(total_records_player)
			count_neutral = 0
			count_positive = 0
			count_negative = 0
			for individual_sentiments in player_sentiment_result['response']['docs']:
				if (individual_sentiments['targeted_sentiment'] == 'neutral'):
					count_neutral = count_neutral + 1
				elif (individual_sentiments['targeted_sentiment'] == 'positive'):
					count_positive = count_positive + 1
				else:
					count_negative = count_negative + 1
			positive_percentage = (float(count_positive) / float(total_records_player)) * 100
			negative_percentage = (float(count_negative) / float(total_records_player)) * 100
			neutral_percentage = (float(count_neutral) / float(total_records_player)) * 100

			player_dict = {'player_name': playerName, 'positive_tweet_count': count_positive, 'negative_tweet_count': count_negative, 'neutral_tweet_count': count_neutral, 'total_count': total_records_player, 'positive_percentage': positive_percentage, 'negative_percentage': negative_percentage, 'neutral_percentage': neutral_percentage}
			player_list.append(player_dict)

	return player_list
	

def sortPlayerList(player_list_to_sort, sortingParameter):
	sortedPlayerlist = sorted(player_list_to_sort, key=itemgetter(sortingParameter), reverse=True)
	#print(sortedPlayerlist)
	return sortedPlayerlist


def ascSortPlayerList(player_list_to_sort, sortingParameter):
	sortedPlayerlist = sorted(player_list_to_sort, key=itemgetter(sortingParameter)) 
	#print(sortedPlayerlist)
	return sortedPlayerlist


def playerSentimentAnalysis(userPlayers):
	get_player_list = getPlayerSentimentList(userPlayers)
	#print(get_player_list)
	player_list_sorted_by_neutral = sortPlayerList(get_player_list, 'neutral_percentage')
	player_list_sorted_by_positive = sortPlayerList(get_player_list, 'positive_percentage')
	player_list_sorted_by_negative = sortPlayerList(get_player_list, 'negative_percentage')

	player_neutral_rank1 = player_list_sorted_by_neutral[0]
	player_neutral_rank2 = player_list_sorted_by_neutral[1]
	player_neutral_rank3 = player_list_sorted_by_neutral[2]

	player_positive_rank1 = player_list_sorted_by_positive[0]
	player_positive_rank2 = player_list_sorted_by_positive[1]
	player_positive_rank3 = player_list_sorted_by_positive[2]

	player_negative_rank1 = player_list_sorted_by_negative[0]
	player_negative_rank2 = player_list_sorted_by_negative[1]
	player_negative_rank3 = player_list_sorted_by_negative[2]

	neutral_chart_dict = {'player_1_name': player_neutral_rank1['player_name'], 'player_1_percentage': player_neutral_rank1['neutral_percentage'], 'player_2_name': player_neutral_rank2['player_name'], 'player_2_percentage': player_neutral_rank2['neutral_percentage'], 'player_3_name': player_neutral_rank3['player_name'], 'player_3_percentage': player_neutral_rank3['neutral_percentage']}

	positive_chart_dict = {'player_1_name': player_positive_rank1['player_name'], 'player_1_percentage': player_positive_rank1['positive_percentage'], 'player_2_name': player_positive_rank2['player_name'], 'player_2_percentage': player_positive_rank2['positive_percentage'], 'player_3_name': player_positive_rank3['player_name'], 'player_3_percentage': player_positive_rank3['positive_percentage']}

	negative_chart_dict = {'player_1_name': player_negative_rank1['player_name'], 'player_1_percentage': player_negative_rank1['negative_percentage'], 'player_2_name': player_negative_rank2['player_name'], 'player_2_percentage': player_negative_rank2['negative_percentage'], 'player_3_name': player_negative_rank3['player_name'], 'player_3_percentage': player_negative_rank3['negative_percentage']}

	return {'neutral': neutral_chart_dict, 'positive': positive_chart_dict, 'negative': negative_chart_dict}
			

def runScript(request):
	try:
		#pdb.set_trace()
		errors = []

		if request.GET['file_name']:
			match_file = request.GET['file_name']

		player_dict = {'V Kohli': 'virat_kohli.json', 'MS Dhoni': 'ms_dhoni.json', 'JE Root': 'joe_root.json', 'CH Gayle': 'chris_gayle.json', 'Yuvraj Singh': 'yuvraj_singh.json', 'JJ Roy': 'jason_roy.json', 'S Dhawan': 'shikhar_dhawan.json', 'EJG Morgan': 'eoin_morgan.json', 'RA Jadeja': 'jadeja.json', 'SK Raina': 'suresh_raina.json', 'MN Samuels': 'marlon_samuels.json'}
		player_match_dict = {'V Kohli': 'kohli_match.json', 'MS Dhoni': 'dhoni_match.json', 'JE Root': 'joe_root_match.json', 'CH Gayle': 'gayle_match.json', 'Yuvraj Singh': 'yuvraj_match.json', 'JJ Roy': 'jason_roy_match.json', 'S Dhawan': 'dhawan_match.json', 'RA Jadeja': 'jadeja_match.json', 'EJG Morgan': 'morgan_match.json', 'SK Raina': 'raina_match.json', 'MN Samuels': 'samuels_match.json'}
		for player_name, player_json in player_dict.items():
			print(player_name)
			print(player_json)
			with open(settings.PLAYER_JSON + player_json) as f:
				player_data = json.load(f)
			#with open(settings.MATCH_JSON + 'IND_vs_NZ_15Mar.json', 'r') as f:
			with open(settings.MATCH_JSON + match_file, 'r') as f:
				match_data = json.load(f)
				
			index = 0
			player_found = False
			innings = 0
			player_index = 0
			
			for batsman in match_data['innings2']['batting']:
				if batsman['player']['playerName'] == player_name:
					player_found = True
					innings = 2
					batsman_det = batsman
					print(batsman_det['runs'])
					player_index = index
					
					if (player_index == 0) or (player_index == 1):
						wickets_fallen = 0
						team_score = 0
					else:
						wickets_fallen = index - 1
						team_score = int((match_data['innings2']['fow'][wickets_fallen -1]['score']).split('-')[1])
					break
				else:
					index = index + 1
			if player_found == False:
				index = 0
				for batsman in match_data['innings1']['batting']:
					if batsman['player']['playerName'] == player_name:
						player_found = True
						innings = 1
						batsman_det = batsman
						player_index = index
						
						if (player_index == 0) or (player_index == 1):
							wickets_fallen = 0
						else:
							wickets_fallen = index - 1
							team_score =  int((match_data['innings1']['fow'][wickets_fallen -1]['score']).split('-')[1])
						break
					else:
						index = index + 1

			if player_found == True:
				print(batsman)
				balls_faced = int(batsman['balls'])
				runs_scored = int(batsman['runs'])        
				strike_rate = float(batsman['strikeRate'])
				status = batsman['status']			
				if status == "not out":
					isOut = 0
				else:
					isOut = 1
				
				N = 0
				CAA = 0
				Gini = 0
				completedInnings = int(player_data[0]['Innings'])
				totalRuns = int(player_data[0]['TotalRuns'])
				totalOuts = int(player_data[0]['TotalOuts'])
				battingImpactList = player_data[0]['BattingImpactList']			
				batting_avg = float(totalRuns + runs_scored) / float(totalOuts + isOut)
				batting_avg = math.ceil(batting_avg*100)/100
				print(batting_avg)
				
				runsInMatches = (player_data[0]['RunsInMatches']).split(',')
				print (runsInMatches)
				
				sum = 0        
				if completedInnings != 0:
					for index in range(len(runsInMatches)):
						for index2 in range(len(runsInMatches)):
							runs1 = int(runsInMatches[index])
							runs2 = int(runsInMatches[index2])
							sum += abs(runs1 - runs2)
					const = 2 *(completedInnings)*(completedInnings)*batting_avg
					Gini = sum/const
					CAA = batting_avg * (1 - Gini)
					print(CAA)
				else:
					CAA = batting_avg

				CAA = math.ceil(CAA*100)/100
					
				matchRuns = 0
				batsman_count=0
				total_balls = 0
				
				#Calculation for batting Impact Factor
				for batsman in match_data['innings2']['batting']:
					matchRuns += int(batsman['runs'])
					total_balls += int(batsman['balls'])
					batsman_count = batsman_count + 1
					
				for batsman in match_data['innings1']['batting']:
					matchRuns += int(batsman['runs'])
					total_balls += int(batsman['balls'])
					batsman_count = batsman_count + 1
				
				baseRuns = float(matchRuns)/float(batsman_count)
				RIS = float(runs_scored/baseRuns)
				print("RIS: ", str(RIS))
				
				SRIS_deno = float(matchRuns)/float(total_balls)
				SRIS = (strike_rate/SRIS_deno) -1
				
				print("SRIS :", str(SRIS))
				
				if (player_index == 0) or (player_index == 1):
					pressure_factor = 0.5
				else:
					pressure_factor = ((wickets_fallen * baseRuns) - team_score)/baseRuns
				print("pressure factor : ", str(pressure_factor))
				print("wickets_fallen : ", str(wickets_fallen))
				print("team_score : ", str(team_score))
				print("baseRuns : ", str(baseRuns))
				PrIS = pressure_factor * RIS
				print("PrIS : ", str(PrIS))

				ChIS = 0.0        
				
				if innings == 2:
					final_score_player_team = int(match_data['innings2']['summary']['total']['score'])
					final_score_opponent_team = int(match_data['innings1']['summary']['total']['score'])
					if (final_score_player_team > final_score_opponent_team) and (isOut == 0):
						ChIS = RIS
				print("ChIS : ", str(ChIS))
				
				batting_impact_score = (RIS + SRIS + PrIS + ChIS )
				batting_impact_score = math.ceil(batting_impact_score*100)/100
				print("final batting_impact_score : ", str(batting_impact_score))
			
				#insert new elements
				player_data[0]['CAA'] = CAA
				player_data[0]['BattingAvg'] = batting_avg
				player_data[0]['TotalRuns'] = totalRuns + runs_scored

				if completedInnings == 0:
					player_data[0]['RunsInMatches'] = str(runs_scored)
				else:
					player_data[0]['RunsInMatches'] = str(player_data[0]['RunsInMatches']) + "," + str(runs_scored)        
				player_data[0]['TotalOuts'] = totalOuts + isOut
				player_data[0]['LastBattingImpact'] = batting_impact_score
				player_data[0]['Innings'] = completedInnings + 1        
				if completedInnings == 0:
					player_data[0]['BattingImpactList'] = str(batting_impact_score)
				else:
					player_data[0]['BattingImpactList'] = str(player_data[0]['BattingImpactList']) + "," + str(batting_impact_score)

				my_player = PlayerStats.objects.get(player_match_name=player_name)
				#my_player_name = my_player.player_name

				my_player.caa = CAA
				my_player.total_runs = totalRuns + runs_scored
				my_player.total_outs = totalOuts + isOut
				my_player.innings = completedInnings + 1
				my_player.batting_impact_list = player_data[0]['BattingImpactList']
				my_player.runs_in_matches = player_data[0]['RunsInMatches']
				my_player.batting_avg = batting_avg
				my_player.last_bat_impact = batting_impact_score
				my_player.save()

					
				#player_match_json_data_variables
				with open(settings.PLAYER_MATCH_JSON + player_match_dict.get(player_name)) as f:
					player_match_data = json.load(f)            
				
				print("player name ::::::::::", str(player_name))
				#pdb.set_trace()

				player_match_data_table = PlayerMatchData()
				player_match_data_table.runs = batsman_det['runs']
				player_match_data_table.status = batsman_det['status']
				player_match_data_table.fours = batsman_det['fours']
				player_match_data_table.six = batsman_det['sixes']
				player_match_data_table.balls_faced = batsman_det['balls']
				player_match_data_table.strike_rate = batsman_det['strikeRate']
				player_match_data_table.match_status = match_data['summary']['matchStatus']
				match_date_data = (match_data['summary']['info']).split('-')
				match_date = (match_date_data[0]).strip()
				match_date = datetime.strptime(match_date, '%d %B %Y')
				fmt = "%Y-%m-%d"
				match_date_formatted = match_date.strftime(fmt) 
				player_match_data_table.match_date = match_date_formatted
				player_match_data_table.tournament = match_data['summary']['tournament']
				player_match_data_table.player_name = my_player
				player_match_data_table.team_name = player_match_data[0]['TeamName']
				player_match_data_table.caa = CAA
				player_match_data_table.last_bat_impact = batting_impact_score

				
				player_team_name = player_match_data[0]['TeamName']

				if player_team_name == match_data['summary']['team1']:       
					player_match_data[0]['OpponentTeamName'] = match_data['summary']['team2']
				else:
					player_match_data[0]['OpponentTeamName'] = match_data['summary']['team1']

				player_match_data_table.opponent_team_name = player_match_data[0]['OpponentTeamName']        

				player_match_data_table.save()

				player_match_data[0]['Runs'] = batsman_det['runs']
				player_match_data[0]['Status'] = batsman_det['status']
				player_match_data[0]['Fours'] = batsman_det['fours']
				player_match_data[0]['Six'] = batsman_det['sixes']
				player_match_data[0]['BallsFaced'] = batsman_det['balls']
				player_match_data[0]['StrikeRate'] = batsman_det['strikeRate']
				player_match_data[0]['MatchStatus'] = match_data['summary']['matchStatus']
				match_date_data = (match_data['summary']['info']).split('-')
				match_date = (match_date_data[0]).strip()
				#match_date = datetime.strptime(match_date, '%d %B %Y')  
				player_match_data[0]['MatchDate'] = match_date
				player_match_data[0]['Tournament'] = match_data['summary']['tournament']

				player_team_name = player_match_data[0]['TeamName']        
				
				if player_team_name ==  match_data['summary']['team1']:       
					player_match_data[0]['OpponentTeamName'] = match_data['summary']['team2']
				else:
					player_match_data[0]['OpponentTeamName'] = match_data['summary']['team1']

				with open(settings.PLAYER_MATCH_JSON + player_match_dict.get(player_name), 'w+') as temp_file:
					temp_file.write(json.dumps(player_match_data))
		  
		
				with open(settings.PLAYER_JSON + player_json, 'w+') as temp_file:
					temp_file.write(json.dumps(player_data))

		response = HttpResponse(json.dumps({'status': 'success'}),  content_type='application/json')

	except:
		errors.append('Error running script')

		response = HttpResponse(json.dumps({'status': 'failure','errors': errors}),  content_type='application/json')
   
	return response


def runScriptIPL(request):
	try:
		#pdb.set_trace()
		errors = []

		if request.GET['file_name']:
			match_file = request.GET['file_name']

		#player_dict = {'V Kohli': 'virat_kohli.json'}

		player_match_dict = {'V Kohli': 'kohli_match.json', 'MS Dhoni': 'dhoni_match.json', 'AJ Finch': 'finch_match.json', 'KP Pietersen': 'kevin_match.json', 'F du Plessis': 'du_plessis_match.json', 'GJ Maxwell': 'maxwell_match.json', 'AB de Villiers': 'de_villiers_match.json', 'AM Rahane': 'rahane_match.json', 'JP Duminy': 'duminy_match.json', 'SK Raina': 'raina_match.json', 'G Gambhir': 'gambhir_match.json', 'RA Jadeja': 'jadeja_match.json', 'RG Sharma': 'sharma_match.json', 'DA Warner': 'warner_match.json'}

		player_dict = {'RA Jadeja': 'jadeja.json', 'GJ Maxwell': 'maxwell.json', 'V Kohli': 'virat_kohli.json', 'MS Dhoni': 'ms_dhoni.json', 'AJ Finch': 'finch.json', 'KP Pietersen': 'kevin.json', 'F du Plessis': 'du_plessis.json', 'AB de Villiers': 'de_villiers.json', 'AM Rahane': 'rahane.json', 'JP Duminy': 'duminy.json', 'SK Raina': 'suresh_raina.json', 'G Gambhir': 'gambhir.json', 'RG Sharma': 'rohit_sharma.json', 'DA Warner': 'warner.json'}

		# player_match_dict = {'V Kohli': 'kohli_match.json', 'MS Dhoni': 'dhoni_match.json', 'AJ Finch': 'finch_match.json', 'KP Pietersen': 'kevin_match.json', 'F du Plessis': 'du_plessis_match.json', 'GJ Maxwell': 'maxwell_match.json', 'AB de Villiers': 'de_villiers_match.json', 'AM Rahane': 'rahane_match.json', 'JP Duminy': 'duminy_match.json', 'SK Raina': 'raina_match.json', 'G Gambhir': 'gambhir_match.json', 'RA Jadeja': 'jadeja_match.json', 'RG Sharma': 'sharma_match.json', 'DA Warner': 'warner_match.json'}
		for player_name, player_json in player_dict.items():
			print(player_name)
			print(player_json)
			with open(settings.IPL_PLAYER_JSON + player_json) as f:
				player_data = json.load(f)
			#with open(settings.IPL_MATCH_JSON + 'IND_vs_NZ_15Mar.json', 'r') as f:
			with open(settings.IPL_MATCH_JSON + match_file, 'r') as f:
				match_data = json.load(f)
				
			index = 0
			player_found = False
			innings = 0
			player_index = 0
			
			for batsman in match_data['innings2']['batting']:
				if batsman['player']['playerName'] == player_name:
					player_found = True
					innings = 2
					batsman_det = batsman
					print(batsman_det['runs'])
					player_index = index
					
					if (player_index == 0) or (player_index == 1):
						wickets_fallen = 0
						team_score = 0
					else:
						wickets_fallen = index - 1
						team_score = int((match_data['innings2']['fow'][wickets_fallen -1]['score']).split('-')[1])
					break
				else:
					index = index + 1
			if player_found == False:
				index = 0
				for batsman in match_data['innings1']['batting']:
					if batsman['player']['playerName'] == player_name:
						player_found = True
						innings = 1
						batsman_det = batsman
						player_index = index
						
						if (player_index == 0) or (player_index == 1):
							wickets_fallen = 0
							team_score = 0
						else:
							wickets_fallen = index - 1
							team_score =  int((match_data['innings1']['fow'][wickets_fallen -1]['score']).split('-')[1])
						break
					else:
						index = index + 1

			if player_found == True:
				print(batsman)
				balls_faced = int(batsman['balls'])
				runs_scored = int(batsman['runs'])        
				strike_rate = float(batsman['strikeRate'])
				status = batsman['status']			
				if status == "not out":
					isOut = 0
				else:
					isOut = 1
				
				N = 0
				CAA = 0
				Gini = 0
				completedInnings = int(player_data[0]['Innings'])
				totalRuns = int(player_data[0]['TotalRuns'])
				totalOuts = int(player_data[0]['TotalOuts'])
				battingImpactList = player_data[0]['BattingImpactList']			
				batting_avg = float(totalRuns + runs_scored) / float(totalOuts + isOut)
				batting_avg = math.ceil(batting_avg*100)/100
				print(batting_avg)
				
				runsInMatches = (player_data[0]['RunsInMatches']).split(',')
				print (runsInMatches)
				
				sum = 0        
				if completedInnings != 0:
					for index in range(len(runsInMatches)):
						for index2 in range(len(runsInMatches)):
							runs1 = int(runsInMatches[index])
							runs2 = int(runsInMatches[index2])
							sum += abs(runs1 - runs2)
					const = 2 *(completedInnings)*(completedInnings)*batting_avg
					Gini = sum/const
					CAA = batting_avg * (1 - Gini)
					print(CAA)
				else:
					CAA = batting_avg

				CAA = math.ceil(CAA*100)/100
					
				matchRuns = 0
				batsman_count=0
				total_balls = 0
				
				#Calculation for batting Impact Factor
				for batsman in match_data['innings2']['batting']:
					matchRuns += int(batsman['runs'])
					total_balls += int(batsman['balls'])
					batsman_count = batsman_count + 1
					
				for batsman in match_data['innings1']['batting']:
					matchRuns += int(batsman['runs'])
					total_balls += int(batsman['balls'])
					batsman_count = batsman_count + 1
				
				baseRuns = float(matchRuns)/float(batsman_count)
				RIS = float(runs_scored/baseRuns)
				print("RIS: ", str(RIS))
				
				SRIS_deno = float(matchRuns)/float(total_balls)
				SRIS = (strike_rate/SRIS_deno) -1
				
				print("SRIS :", str(SRIS))


				
				if (player_index == 0) or (player_index == 1):
					pressure_factor = 0.5
				else:
					pressure_factor = ((wickets_fallen * baseRuns) - team_score)/baseRuns
				print("pressure factor : ", str(pressure_factor))
				print("wickets_fallen : ", str(wickets_fallen))
				print("team_score : ", str(team_score))
				print("baseRuns : ", str(baseRuns))
				PrIS = pressure_factor * RIS
				print("PrIS : ", str(PrIS))

				ChIS = 0.0        
				
				if innings == 2:
					final_score_player_team = int(match_data['innings2']['summary']['total']['score'])
					final_score_opponent_team = int(match_data['innings1']['summary']['total']['score'])
					if (final_score_player_team > final_score_opponent_team) and (isOut == 0):
						ChIS = RIS
				print("ChIS : ", str(ChIS))
				
				batting_impact_score = (RIS + SRIS + PrIS + ChIS )
				batting_impact_score = math.ceil(batting_impact_score*100)/100
				print("final batting_impact_score : ", str(batting_impact_score))
			
				#insert new elements
				player_data[0]['CAA'] = CAA
				player_data[0]['BattingAvg'] = batting_avg
				player_data[0]['TotalRuns'] = totalRuns + runs_scored

				if completedInnings == 0:
					player_data[0]['RunsInMatches'] = str(runs_scored)
				else:
					player_data[0]['RunsInMatches'] = str(player_data[0]['RunsInMatches']) + "," + str(runs_scored)        
				player_data[0]['TotalOuts'] = totalOuts + isOut
				player_data[0]['LastBattingImpact'] = batting_impact_score
				player_data[0]['Innings'] = completedInnings + 1        
				if completedInnings == 0:
					player_data[0]['BattingImpactList'] = str(batting_impact_score)
				else:
					player_data[0]['BattingImpactList'] = str(player_data[0]['BattingImpactList']) + "," + str(batting_impact_score)

				my_player = PlayerStats.objects.get(player_match_name=player_name)
				#my_player_name = my_player.player_name

				my_player.caa = CAA
				my_player.total_runs = totalRuns + runs_scored
				my_player.total_outs = totalOuts + isOut
				my_player.innings = completedInnings + 1
				my_player.batting_impact_list = player_data[0]['BattingImpactList']
				my_player.runs_in_matches = player_data[0]['RunsInMatches']
				my_player.batting_avg = batting_avg
				my_player.last_bat_impact = batting_impact_score
				my_player.save()

					
				#player_match_json_data_variables
				with open(settings.IPL_PLAYER_MATCH_JSON + player_match_dict.get(player_name)) as f:
					player_match_data = json.load(f)            
				
				print("player name ::::::::::", str(player_name))
				#pdb.set_trace()

				player_match_data_table = PlayerMatchData()
				player_match_data_table.runs = batsman_det['runs']
				player_match_data_table.status = batsman_det['status']
				player_match_data_table.fours = batsman_det['fours']
				player_match_data_table.six = batsman_det['sixes']
				player_match_data_table.balls_faced = batsman_det['balls']
				player_match_data_table.strike_rate = batsman_det['strikeRate']
				player_match_data_table.match_status = match_data['summary']['matchStatus']
				match_date_data = (match_data['summary']['info']).split('-')
				match_date = (match_date_data[0]).strip()
				match_date = datetime.strptime(match_date, '%d %B %Y')
				fmt = "%Y-%m-%d"
				match_date_formatted = match_date.strftime(fmt) 
				player_match_data_table.match_date = match_date_formatted
				player_match_data_table.tournament = match_data['summary']['tournament']
				player_match_data_table.player_name = my_player
				player_match_data_table.team_name = player_match_data[0]['TeamName']
				player_match_data_table.caa = CAA
				player_match_data_table.last_bat_impact = batting_impact_score

				
				player_team_name = player_match_data[0]['TeamName']

				if player_team_name == match_data['summary']['team1']:       
					player_match_data[0]['OpponentTeamName'] = match_data['summary']['team2']
				else:
					player_match_data[0]['OpponentTeamName'] = match_data['summary']['team1']

				player_match_data_table.opponent_team_name = player_match_data[0]['OpponentTeamName']        

				player_match_data_table.save()

				player_match_data[0]['Runs'] = batsman_det['runs']
				player_match_data[0]['Status'] = batsman_det['status']
				player_match_data[0]['Fours'] = batsman_det['fours']
				player_match_data[0]['Six'] = batsman_det['sixes']
				player_match_data[0]['BallsFaced'] = batsman_det['balls']
				player_match_data[0]['StrikeRate'] = batsman_det['strikeRate']
				player_match_data[0]['MatchStatus'] = match_data['summary']['matchStatus']
				match_date_data = (match_data['summary']['info']).split('-')
				match_date = (match_date_data[0]).strip()
				#match_date = datetime.strptime(match_date, '%d %B %Y')  
				player_match_data[0]['MatchDate'] = match_date
				player_match_data[0]['Tournament'] = match_data['summary']['tournament']

				player_team_name = player_match_data[0]['TeamName']        
				
				if player_team_name ==  match_data['summary']['team1']:       
					player_match_data[0]['OpponentTeamName'] = match_data['summary']['team2']
				else:
					player_match_data[0]['OpponentTeamName'] = match_data['summary']['team1']

				with open(settings.IPL_PLAYER_MATCH_JSON + player_match_dict.get(player_name), 'w+') as temp_file:
					temp_file.write(json.dumps(player_match_data))
		  
		
				with open(settings.IPL_PLAYER_JSON + player_json, 'w+') as temp_file:
					temp_file.write(json.dumps(player_data))

		response = HttpResponse(json.dumps({'status': 'success'}),  content_type='application/json')

	except:
		errors.append('Error running script')

		response = HttpResponse(json.dumps({'status': 'failure','errors': errors}),  content_type='application/json')
   
	return response
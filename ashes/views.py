from urllib.request import Request, urlopen
import urllib.parse
import json
from django.shortcuts import render
from django.conf import settings
import pdb
from .models import PlayerStats, UserPlayers


def home(request):
	try:
		errors = []
		#pdb.set_trace()

		players = PlayerStats.objects.all()
		userPlayers = UserPlayers.objects.all()
		#pdb.set_trace()

		get_player_list = getPlayerSentimentList(userPlayers)
		print(get_player_list)

		context = {'allPlayerList': players, 'myPlayerList': userPlayers}

	except:
		
		errors.append('Error Completing request')
		context = {'errors': errors}

	return render(request, "playercompare.html", context)


def playerCompareAction(request):
	try:
		errors = []
		if request.GET['myPlayerSelect']:
			my_player = UserPlayers.objects.get(player_name=request.GET['myPlayerSelect'])
		if request.GET['allPlayerSelect']:
			other_player = PlayerStats.objects.get(player_name=request.GET['allPlayerSelect'])

		my_player_caa = my_player.player_name.caa
		other_player_caa = other_player.caa

		if my_player_caa > other_player_caa:
			message = 'We recommend ' + my_player.player_name.player_name + ' over ' + other_player.player_name
			print(message)
		else:
			message = 'We recommend ' + other_player.player_name + ' over ' + my_player.player_name.player_name
			print(message)

		players = PlayerStats.objects.all()
		userPlayers = UserPlayers.objects.all()

		
		context = {'allPlayerList': players, 'myPlayerList': userPlayers, 'myPlayer': my_player, 'otherPlayer': other_player, 'message': message}

	except:
		errors.append('Error Completing request')
		context = {'errors': errors}

	return render(request, "playercompare.html", context)


def makeSolrCall(search_query, type):
    #pdb.set_trace()

    if type == "tweet":
        request_params = urllib.parse.urlencode(
            {'q': '*:*', 'wt': 'json', 'indent': 'true', 'rows': 1000, 'start': 0, 'fl':'targeted_sentiment', 'fq':'search_target:'+search_query})
        request_params = request_params.encode('utf-8')
        req = urllib.request.urlopen('http://localhost:8983/solr/cricketTweetsCore/select',
                                     request_params)

    content = req.read()
    decoded_json_content = json.loads(content.decode())
    return decoded_json_content


def getPlayerSentimentList(UserPlayers):

	player_list = []

	for individual_player in UserPlayers:
			playerName = individual_player.player_name.player_name
			playerSearchTarget = individual_player.search_target
			player_sentiment_result = makeSolrCall(playerSearchTarget, 'tweet')

			total_records_player = player_sentiment_result['response']['numFound']
			print(total_records_player)
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
			positive_percentage = ( float(count_positive) / float(total_records_player) ) * 100
			negative_percentage = ( float(count_negative) / float(total_records_player) ) * 100
			neutral_percentage = ( float(count_neutral) / float(total_records_player) ) * 100

			player_dict = {'player_name': playerName, 'positive_tweet_count': count_positive, 'negative_tweet_count': count_negative, 'neutral_tweet_count': count_neutral, 'total_count': total_records_player, 'positive_percentage': positive_percentage, 'negative_percentage': negative_percentage, 'neutral_percentage': neutral_percentage}
			player_list.append(player_dict)

	return player_list

			    

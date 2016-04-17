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



def home(request):
	try:
		errors = []
		#pdb.set_trace()

		if request.method == 'GET' and 'week' in request.GET:
			print(request.GET['week'])
			week = request.GET['week']
		else:
			week = 'week1'
			print(week)


		players = PlayerStats.objects.all()
		userPlayers = UserPlayers.objects.all()
		#pdb.set_trace()

		sentiment_wise_player_dict = playerSentimentAnalysis(userPlayers, week)
		neutral_chart_dict = sentiment_wise_player_dict['neutral']
		positive_chart_dict = sentiment_wise_player_dict['positive']
		negative_chart_dict = sentiment_wise_player_dict['negative']

		context = {'allPlayerList': players, 'myPlayerList': userPlayers, 'neutral_player_list' : neutral_chart_dict, 'positive_player_list': positive_chart_dict, 'negative_player_list': negative_chart_dict}

	except:
		
		errors.append('Error Completing request')
		context = {'errors': errors}

	return render(request, "playercompare.html", context)

def playerPage(request):
		try:
			errors = []
			userPlayers = UserPlayers.objects.all()

			if request.method == 'GET' and 'week' in request.GET:
				print(request.GET['week'])
				week = request.GET['week']
			else:
				week = 'week1'
				print(week)

			if request.method == 'GET' and 'myPlayerSelect' in request.GET:				
				my_player = UserPlayers.objects.get(player_name=request.GET['myPlayerSelect'])
				player_wise_articles = makeSolrCall(my_player.articles_search_target, 'articles', week)
				player_wise_tweets = makeSolrCall(my_player.search_target, 'playerTweets', week)
				print(player_wise_articles['response']['docs'])
				
				player_match_data = []

				for player_match_record in PlayerMatchData.objects.filter(player_name=request.GET['myPlayerSelect']):
					player_match_data.append(player_match_record)
				print("printing all rows....")
				print (player_match_data)

				player_sentiment_dict = getIndividualPlayerSentiment(my_player, week)

				context = {'myPlayerList': userPlayers, 'articles' : player_wise_articles['response']['docs'], 'myPlayer' : my_player,
				'playerTweets' : player_wise_tweets['response']['docs'], 'match_data' : player_match_data, 'player_sentiment_dict': player_sentiment_dict}
			else:
				context = {'myPlayerList': userPlayers}

		except:
			errors.append('Error Completing request')
			context = {'errors': errors}

		return render(request, "player.html", context)


def playerCompareAction(request):
	try:
		errors = []
		if request.GET['myPlayerSelect']:
			my_player = UserPlayers.objects.get(player_name=request.GET['myPlayerSelect'])
		if request.GET['allPlayerSelect']:
			other_player = PlayerStats.objects.get(player_name=request.GET['allPlayerSelect'])
		if request.method == 'GET' and 'week' in request.GET:
			print(request.GET['week'])
			week = request.GET['week']

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

		sentiment_wise_player_dict = playerSentimentAnalysis(userPlayers, week)
		neutral_chart_dict = sentiment_wise_player_dict['neutral']
		positive_chart_dict = sentiment_wise_player_dict['positive']
		negative_chart_dict = sentiment_wise_player_dict['negative']
		
		context = {'allPlayerList': players, 'myPlayerList': userPlayers, 'myPlayer': my_player, 'otherPlayer': other_player, 'message': message, 'neutral_player_list' : neutral_chart_dict, 'positive_player_list': positive_chart_dict, 'negative_player_list': negative_chart_dict}

	except:
		errors.append('Error Completing request')
		context = {'errors': errors}

	return render(request, "playercompare.html", context)


def makeSolrCall(search_query, queryType, week):
	
	#curl --globoff 'http://localhost:8983/solr/cricketTweetsCore/select?&wt=json&q=*kohli*&defType=dismax&qf=keywords+entity+text&indent=true&start=0&rows=100&bq=date^20+retweets^10+favorites^5&sort=date+desc,retweets+desc,favorites+desc&fq=date:[2016-03-25T00:00:00Z%20TO%202016-04-03T00:00:00Z]'

	if week == 'week1':
		date = 'date:[2016-03-15T00:00:00Z TO 2016-03-20T00:00:00Z]'
	elif week == 'week2':
		date = 'date:[2016-03-21T00:00:00Z TO 2016-03-27T00:00:00Z]'
	else:
		date = 'date:[2016-03-28T00:00:00Z TO 2016-04-04T00:00:00Z]'

	if queryType == "tweet":
		request_params = urllib.parse.urlencode(
			{'q': '*'+search_query+'*', 'wt': 'json', 'indent': 'true', 'rows': 1000, 'start': 0, 'defType': 'dismax','qf': 'search_target','fl':'targeted_sentiment', 'fq': date})
		request_params = request_params.encode('utf-8')
		req = urllib.request.urlopen('http://localhost:8983/solr/cricketTweetsCore/select',
									 request_params)
	elif queryType == "articles":
		#pdb.set_trace()
		request_params = urllib.parse.urlencode(
			{'q': '*'+search_query+'*', 'wt': 'json', 'indent': 'true', 'rows': 3, 'start': 0, 'defType': 'dismax','qf': 'title keywords summary content','fl':'title,article_url,date,summary', 'fq': date, 'bq': 'title^20 summary^10 date^5 ', 'sort': 'date desc'})
		request_params = request_params.encode('utf-8')
		req = urllib.request.urlopen('http://localhost:7574/solr/articlesCore/select',
									 request_params)
	elif queryType == "playerTweets":
		#pdb.set_trace()
		request_params = urllib.parse.urlencode(
			{'q': '*'+search_query+'*', 'wt': 'json', 'indent': 'true', 'rows': 100, 'start': 0, 'defType': 'dismax', 'qf': 'keywords entity text', 'bq': 'date^20 retweets^10 favorites^5', 'sort': 'date desc,retweets desc,favorites desc','fq': date})
		request_params = request_params.encode('utf-8')
		req = urllib.request.urlopen('http://localhost:8983/solr/cricketTweetsCore/select',
									 request_params)

	content = req.read()
	decoded_json_content = json.loads(content.decode())
	return decoded_json_content


def getIndividualPlayerSentiment(UserPlayers, week):
	#player_list = []
	playerName = UserPlayers.player_name.player_name
	playerSearchTarget = UserPlayers.search_target
	player_sentiment_result = makeSolrCall(playerSearchTarget, 'tweet', week)

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
	positive_percentage = ( float(count_positive) / float(total_records_player) ) * 100
	negative_percentage = ( float(count_negative) / float(total_records_player) ) * 100
	neutral_percentage = ( float(count_neutral) / float(total_records_player) ) * 100

	player_dict = {'player_name': playerName, 'positive_tweet_count': count_positive, 'negative_tweet_count': count_negative, 'neutral_tweet_count': count_neutral, 'total_count': total_records_player, 'positive_percentage': positive_percentage, 'negative_percentage': negative_percentage, 'neutral_percentage': neutral_percentage}
	# player_list.append(player_dict)

	return player_dict


def getPlayerSentimentList(UserPlayers, week):

	player_list = []

	for individual_player in UserPlayers:
			playerName = individual_player.player_name.player_name
			playerSearchTarget = individual_player.search_target
			player_sentiment_result = makeSolrCall(playerSearchTarget, 'tweet', week)

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
			positive_percentage = ( float(count_positive) / float(total_records_player) ) * 100
			negative_percentage = ( float(count_negative) / float(total_records_player) ) * 100
			neutral_percentage = ( float(count_neutral) / float(total_records_player) ) * 100

			player_dict = {'player_name': playerName, 'positive_tweet_count': count_positive, 'negative_tweet_count': count_negative, 'neutral_tweet_count': count_neutral, 'total_count': total_records_player, 'positive_percentage': positive_percentage, 'negative_percentage': negative_percentage, 'neutral_percentage': neutral_percentage}
			player_list.append(player_dict)

	return player_list

def sortPlayerList(player_list_to_sort, sortingParameter):
	sortedPlayerlist = sorted(player_list_to_sort, key=itemgetter(sortingParameter), reverse=True) 
	#print(sortedPlayerlist)
	return sortedPlayerlist

def playerSentimentAnalysis(userPlayers, week):
	get_player_list = getPlayerSentimentList(userPlayers, week)
	#print(get_player_list)
	player_list_sorted_by_neutral = sortPlayerList(get_player_list, 'neutral_percentage')
	player_list_sorted_by_positive = sortPlayerList(get_player_list, 'positive_percentage')
	player_list_sorted_by_negative = sortPlayerList(get_player_list, 'negative_percentage')

	player_neutral_rank1 = player_list_sorted_by_neutral[0]
	player_neutral_rank2 = player_list_sorted_by_neutral[1]
	player_neutral_rank3 = player_list_sorted_by_neutral[2]
	# print(player_list_sorted_by_neutral)
	# print(player_neutral_rank2['player_name'])
	# print(player_neutral_rank3['player_name'])

	player_positive_rank1 = player_list_sorted_by_positive[0]
	player_positive_rank2 = player_list_sorted_by_positive[1]
	player_positive_rank3 = player_list_sorted_by_positive[2]

	player_negative_rank1 = player_list_sorted_by_negative[0]
	player_negative_rank2 = player_list_sorted_by_negative[1]
	player_negative_rank3 = player_list_sorted_by_negative[2]

	neutral_chart_dict = { 'player_1_name' : player_neutral_rank1['player_name'], 'player_1_percentage' : player_neutral_rank1['neutral_percentage'], 'player_2_name' : player_neutral_rank2['player_name'], 'player_2_percentage' : player_neutral_rank2['neutral_percentage'], 'player_3_name' : player_neutral_rank3['player_name'], 'player_3_percentage' : player_neutral_rank3['neutral_percentage']}

	positive_chart_dict = { 'player_1_name' : player_positive_rank1['player_name'], 'player_1_percentage' : player_positive_rank1['positive_percentage'], 'player_2_name' : player_positive_rank2['player_name'], 'player_2_percentage' : player_positive_rank2['positive_percentage'], 'player_3_name' : player_positive_rank3['player_name'], 'player_3_percentage' : player_positive_rank3['positive_percentage']}

	negative_chart_dict = { 'player_1_name' : player_negative_rank1['player_name'], 'player_1_percentage' : player_negative_rank1['negative_percentage'], 'player_2_name' : player_negative_rank2['player_name'], 'player_2_percentage' : player_negative_rank2['negative_percentage'], 'player_3_name' : player_negative_rank3['player_name'], 'player_3_percentage' : player_negative_rank3['negative_percentage']}

	return {'neutral' : neutral_chart_dict, 'positive' : positive_chart_dict, 'negative' : negative_chart_dict}
			


def runScript(request):
	try:
		#pdb.set_trace()
		errors = []
		#raise Exception('lalala')

		player_dict = { 'V Kohli' : 'virat_kohli.json', 'MS Dhoni' : 'ms_dhoni.json', 'Joe Root': 'joe_root.json', 'CH Gayle' : 'chris_gayle.json', 'Yuvraj Singh' : 'yuvraj_singh.json', 'Jason Roy': 'jason_roy.json', 'S Dhawan' : 'shikhar_dhawan.json'}
		player_match_dict = {'V Kohli' : 'kohli_match.json', 'MS Dhoni' : 'dhoni_match.json', 'Joe Root': 'joe_root_match.json', 'CH Gayle' : 'gayle_match.json', 'Yuvraj Singh' : 'yuvraj_match.json', 'Jason Roy': 'jason_roy_match.json', 'S Dhawan' : 'dhawan_match.json'}
		for player_name, player_json in player_dict.items():
			print(player_name)
			print(player_json)
			with open('/home/rachna/PlayerProcess/scriptjsonfiles/playerJson/' + player_json ) as f:
				player_data = json.load(f)
			with open('/home/rachna/PlayerProcess/scriptjsonfiles/T20_Match_Data/IND_vs_BAN_23Mar.json', 'r') as f:
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
						wickets_fallen = index-1
						team_score =  int((match_data['innings2']['fow'][wickets_fallen -1]['score']).split('-')[1])
					break
				else:
					index = index +1
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
				
		#        print "balls_faced: "+str(balls_faced)
		#        print "runs_scored: "+str(runs_scored)
		#        print "strike_rate: "+str(strike_rate)
		#        print "status: "+str(status)
				
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
				
		#        print player_data
		#        print str(player_data[0]['Innings'])
		#        print str(player_data[0]['CAA'])
		#        print str(player_data[0]['TotalRuns'])
		#        print str(player_data[0]['TotalOuts'])
		#        print str(player_data[0]['BattingImpactList'])
				
				batting_avg = float(totalRuns + runs_scored) / float(totalOuts + isOut)
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
		#        print "batsman count : "+str(batsman_count)        
		#        print "my runs : "+str(runs_scored)
		#        print "matchruns : "+str(matchRuns)
		#        print "baseruns : "+str(baseRuns)
				print("RIS: ", str(RIS))
				
				SRIS_deno = float(matchRuns)/float(total_balls)
				SRIS = (strike_rate/SRIS_deno) -1
				
		#        print "strike rate : "+str(strike_rate)
		#        print "SRIS_deno :"+str(SRIS_deno)
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
				with open('/home/rachna/PlayerProcess/scriptjsonfiles/player_match_Json/' +  player_match_dict.get(player_name)) as f:
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

				with open('/home/rachna/PlayerProcess/scriptjsonfiles/player_match_Json/' + player_match_dict.get(player_name), 'w+') as temp_file:
					temp_file.write(json.dumps(player_match_data))
		  
		
				with open('/home/rachna/PlayerProcess/scriptjsonfiles/playerJson/' + player_json, 'w+') as temp_file:
					temp_file.write(json.dumps(player_data))

		response = HttpResponse(json.dumps({'status': 'success'}),  content_type='application/json')

	except:
		errors.append('Error running script')

		response = HttpResponse(json.dumps({'status': 'failure','errors': errors}),  content_type='application/json')
   
	return response 
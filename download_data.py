import os
import json
import time
import datetime
from io import StringIO
from collections import OrderedDict

import requests
from lxml import etree
from lxml.cssselect import CSSSelector

def duration_to_seconds(duration):
	x = time.strptime(duration.split(",")[0],'%H:%M:%S')
	return datetime.timedelta(hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec).total_seconds()

def parse_listings_page(http_response):
	tree   = etree.parse(StringIO(http_response.text), etree.HTMLParser())
	css_row =  CSSSelector("li.list-group-item.row:not(list-group-header)")
	css_place = CSSSelector("div.row div.place-primary")
	css_place_ak = CSSSelector("div.row div.place-secondary")
	css_name = CSSSelector("div.row h4.type-fullname a")
	css_navigation = CSSSelector("ul.pagination li:last-child")
	results = []
	i = 0
	for row in css_row(tree):
		try:
			place = css_place(row)[0].text.strip()
			if place!="Platz":
				place_ak = css_place_ak(row)[0].text
				if place_ak!=None:
					place_ak = int(place_ak.strip())

				results.append(dict(
					place = place,
					place_ak = place_ak,
					name = css_name(row)[0].text.strip(),			
					url = css_name(row)[0].get('href')
				))
		except Exception as e:
			print("Exception at element %s, place %s. %s" % (i, place, e))
		i+=1
	next_page_link = None
	try:
		navigation = css_navigation(tree)[0]
		if navigation.get("class") == "pages-nav-button":
			# there is one more page
			next_page_link = navigation.cssselect("a")[0].get("href")
	except:
		pass
	return (results, next_page_link)

def parse_personal_page(http_response, event_date, keep_splits_without_time=True, exclude_splits=("Run Total", "Best Run Lap")):
	tree   = etree.parse(StringIO(http_response.text), etree.HTMLParser())
	
	if exclude_splits == None:
		exclude_splits = ()
	#css_fullname = CSSSelector("div.detail-box.box-general td.f-__fullname")
	#fullname = css_fullname(tree)[0].text.strip()

	css_start_number = CSSSelector("div.detail-box.box-general td.f-start_no_text")
	start_number = css_start_number(tree)[0].text.strip()

	# for hyrox, startnumber is hh|mm|sequential
	start_time = event_date + datetime.timedelta(hours=int(start_number[0:2]), minutes=int(start_number[2:4]))

	css_total_time = CSSSelector("div.detail-box.box-totals td.f-time_finish_netto")
	total_time = duration_to_seconds(css_total_time(tree)[0].text.strip())
	
	css_judge_bonus = CSSSelector("div.detail-box.box-judges tr.f-gimmick_03 td")
	bonus = css_judge_bonus(tree)[0].text
	if bonus:
		bonus = bonus.strip()
	
	css_judge_penalty = CSSSelector("div.detail-box.box-judges tr.f-gimmick_01 td")
	penalty = css_judge_penalty(tree)[0].text
	if penalty:
		penalty = penalty.strip()
	
	# analyze the run-data table
	css_run_tablerow = CSSSelector("div.detail-box.box-other table tbody tr")
	css_run_header = CSSSelector("th")
	css_run_time = CSSSelector("td:first-of-type")

	splits = OrderedDict()
	i = 1
	for row in css_run_tablerow(tree):
		split = css_run_header(row)[0].text
		if split != None and split.strip() not in exclude_splits:
			split = split.strip()
			time = css_run_time(row)[0].text
			if time != None:
				time = duration_to_seconds(time.strip())
		
			if time!=None or keep_splits_without_time:
				splits["%02d_%s" % (i, split)] = time
				i += 1
	return dict(
		start_time = start_time.strftime("%Y-%m-%d %H:%M:%S"),
		start_number = start_number,
		judges_bonus = bonus,
		judges_penalty = penalty,
		total_time = total_time,
		splits = splits
	)


def analyze_ranking(event_id, event_main_group, event_name, event_date, base_url, division, category):
	try:
		event_date = datetime.datetime.strptime(event_date, "%Y-%m-%d")
	except:
		raise ValueError("analyze_ranking: wrong event_date provided, accepted format: YYYY-MM-DD, provided: '%s'" % event_date)

	if category=="men":
		sex = "M"
	elif category=="women":
		sex = "W"
	elif category=="mixed":
		sex = "X"
	else:
		raise ValueError("analyze_ranking: wrong category provided, accepted: men/women/mixed, provided: '%s'" % category)
	params_post = {
		"event_main_group": event_main_group,
		"event": event_id,
		"search[sex]": sex,
		"lang": "DE",
		"startpage": "start_responsive",
		"startpage_type": "lists",
		"ranking": "time_finish_netto",
 		"search[age_class]": "%",
		"search[nation]": "%",
		"num_results": "100",
		"submit": None,
	} 	
	all_results = []
	
	r = requests.post(base_url, params=dict(pid="list"), data=params_post)	
	partial_results, next_page = parse_listings_page(r)	
	all_results.extend(partial_results)
	
	while next_page != None:
		r = requests.get(base_url + next_page)
		partial_results, next_page = parse_listings_page(r)
		all_results.extend(partial_results)
	print("\t\tRecorded %s rankings" % len(all_results))
	i=0
	for performance in all_results:
		performance['url'] = base_url + performance['url']
		performance['event'] = event_name
		performance['event_occurrence'] = event_main_group
		performance['category'] = category
		performance['division'] = division
		r = requests.get(performance['url'])	
		performance.update(parse_personal_page(r, event_date, 
			keep_splits_without_time=True, 
			exclude_splits=("Run Total", "Best Run Lap")))
		i += 1
		if i%25 == 0:
			print("\t\t\tAnalyzed %i rankings" % i)
	print("\t\tCompleted analyzing %i rankings" % i)
	return all_results


events = [
	dict(
		event_name="Hyrox", 
		event_main_group = "2018 Stuttgart",
		event_date="2018-12-15", 
		base_url="http://hyrox.r.mikatiming.de/2018/",
		rankings = [
			dict(event_id="H_999999212F07B50000000052", category="men", division="regular"),
			dict(event_id="H_999999212F07B50000000052", category="women", division="regular"),
			dict(event_id="HPRO_999999212F07B50000000052", category="men", division="pro"),
			dict(event_id="HPRO_999999212F07B50000000052", category="women", division="pro")
		]
		),
	dict(
		event_name="Hyrox", 
		event_main_group = "2018 Wien",
		event_date="2018-12-08", 
		base_url="http://hyrox.r.mikatiming.de/2018/",
		rankings = [
			dict(event_id="H_999999212F07B50000000051", category="men", division="regular"),
			dict(event_id="H_999999212F07B50000000051", category="women", division="regular"),
			dict(event_id="HPRO_999999212F07B50000000051", category="men", division="pro"),
			dict(event_id="HPRO_999999212F07B50000000051", category="women", division="pro"),
			#dict(event_id="HD_999999212F07B50000000051", category="men", division="doubles"),
			#dict(event_id="HD_999999212F07B50000000051", category="women", division="doubles"),
			#dict(event_id="HD_999999212F07B50000000051", category="x", division="doubles")
			
		]
	),
	dict(
		event_name="Hyrox", 
		event_main_group = "2018 Essen",
		event_date="2018-11-10", 
		base_url="http://hyrox.r.mikatiming.de/2018/",
		rankings = [
			dict(event_id="H_999999212F07B5000000003D", category="men", division="regular"),
			dict(event_id="H_999999212F07B5000000003D", category="women", division="regular"),
			dict(event_id="HPRO_999999212F07B5000000003D", category="men", division="pro"),
			dict(event_id="HPRO_999999212F07B5000000003D", category="women", division="pro"),
			#dict(event_id="HD_999999212F07B5000000003D", category="men", division="doubles"),
			#dict(event_id="HD_999999212F07B5000000003D", category="women", division="doubles"),
			#dict(event_id="HD_999999212F07B5000000003D", category="x", division="doubles")
			
		]
	),
	dict(
		event_name="Hyrox", 
		event_main_group = "2018 Hamburg",
		event_date="2018-11-03", 
		base_url="http://hyrox.r.mikatiming.de/2018/",
		rankings = [
			dict(event_id="H_999999212F07B50000000029", category="men", division="regular"),
			dict(event_id="H_999999212F07B50000000029", category="women", division="regular"),
			dict(event_id="HPRO_999999212F07B50000000029", category="men", division="pro"),
			dict(event_id="HPRO_999999212F07B50000000029", category="women", division="pro"),
			#dict(event_id="HD_999999212F07B50000000029", category="men", division="doubles"),
			#dict(event_id="HD_999999212F07B50000000029", category="women", division="doubles"),
			#dict(event_id="HD_999999212F07B50000000029", category="x", division="doubles")
			
		]
	),
	dict(
		event_name="Hyrox", 
		event_main_group = "2018 Leipzig",
		event_date="2018-10-20", 
		base_url="http://hyrox.r.mikatiming.de/2018/",
		rankings = [
			dict(event_id="H_999999212F07B50000000015", category="men", division="regular"),
			dict(event_id="H_999999212F07B50000000015", category="women", division="regular"),
			dict(event_id="HPRO_999999212F07B50000000015", category="men", division="pro"),
			dict(event_id="HPRO_999999212F07B50000000015", category="women", division="pro"),
			#dict(event_id="HD_999999212F07B50000000015", category="men", division="doubles"),
			#dict(event_id="HD_999999212F07B50000000015", category="women", division="doubles"),
			#dict(event_id="HD_999999212F07B50000000015", category="x", division="doubles")
			
		]
	),

]

all_results = []
for event in events:
	filename = "%(event_name)s - %(event_main_group)s.json" % event
	print("Analyzing event %(event_name)s - %(event_main_group)s" % event)
	print("\tWriting all data to file '%s'" % filename)
	with open(filename, "a") as jsonfile:
		for ranking in event['rankings']:
			print("\tAnalyzing rankings for %(division)s - %(category)s" % ranking)
			results = analyze_ranking(
					event_id=ranking['event_id'],
					event_name=event['event_name'], 
					event_main_group=event['event_main_group'], 
					event_date=event['event_date'], 
					division=ranking['division'],
					category=ranking['category'], 
					base_url=event['base_url'], 
			)
			for res in results:
				jsonfile.write("%s\n" % json.dumps(res, sort_keys=True))
			all_results.extend(results)
	print("Done with event %(event_name)s - %(event_main_group)s.\n" % event)


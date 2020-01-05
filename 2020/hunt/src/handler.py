import json
import yaml
import urllib.parse
import boto3
import time
import string
import base64
from datetime import datetime, timedelta
import copy


with open('game_ids.yaml') as file:
    game_ids = yaml.load(file, Loader=yaml.FullLoader)
with open('game_hashes.yaml') as file:
    game_hash_list = yaml.load(file, Loader=yaml.FullLoader)['hashes']

#VALID_URIS = ['/hunt/prosperity', '/hunt/insight', '/hunt/success', '/hunt/vision']
TEAMS = ['Prosperity', 'Insight', 'Success', 'Vision']
VALID_URIS = list(map(lambda t: f'/hunt/{t}', TEAMS))
VERSION = 0


def log_success(team, score):
    team = team.lower()

    client = boto3.client('logs', 'us-east-1')
    params = {
        'logGroupName': 'brycon/hunt',
        'logStreamName': f'{team}_successes'
    }

    # create log stream if doesn't exist
    try:
        client.create_log_stream(**params)
    except:
        pass

    # prepare a simple log event capturing the score

    params['logEvents'] = [
        {
            'timestamp': int(round(time.time() * 1000)),
            'message': f'{team} {score}'
        }
    ]

    # find out if we've previously written to the log stream

    response = client.describe_log_streams(
        logGroupName=params['logGroupName'],
        logStreamNamePrefix=params['logStreamName']
    )
    log_stream = response['logStreams'][0]

    # use the stream sequence token if found

    if 'uploadSequenceToken' in log_stream:
        params['sequenceToken'] = log_stream['uploadSequenceToken']

    client.put_log_events(**params)


def get_cloudfront_response(body):
    return {
        'body': body,
        'bodyEncoding': 'text',
        'headers': {
            'content-type': [{
                'key': 'Content-Type',
                'value': 'text/html'
             }],
            'x-function-version': [{
                'key': 'X-Function-Version',
                'value': VERSION
            }]
        },
        'status': '200'
    }


def get_response_from_template(name, params):
    with open(name, 'r') as file:
        data = file.read()

    t = string.Template(data)
    return get_cloudfront_response(t.substitute(**params))


def get_answers(request):
    FINISHED = 'FINISHED'
    querystring = request['querystring']
    if querystring:
        query_params = urllib.parse.parse_qs(querystring)
        h = query_params['h'][0]
        if h == FINISHED:
            return get_pick_team_response()
        full = (query_params['full'][0] == 'True')
    else:
        h = game_hash_list[0]
        full = False

    if full:
        i = game_hash_list.index(h)
        if i + 1 == len(game_hash_list):
            next_h = FINISHED
        else:
            next_h = game_hash_list[i + 1]
    else:
        next_h = h

    params = {
        'image_name': 'full/' + h if full else h,
        'uri': '{}?full={}&h={}'.format(request['uri'], not full, next_h),
        'image_type': '{} Box Image'.format('Full' if full else 'Partial')
    }

    with open('a.html', 'r') as file:
        data = file.read()

    t = string.Template(data)

    return get_cloudfront_response(t.substitute(**params))


def get_scores():
    queries = []
    for team in TEAMS:
        queries.append({
            'Id': team.lower(),
            'Label': team,
            'MetricStat': {
                'Metric': {
                    'Namespace': 'Brycon',
                    'MetricName': 'Team{}Score'.format(team),
                },
                'Period': 3600,
                'Stat': 'Maximum',
                'Unit': 'None'
            }
        })

    now = datetime.utcnow()
    start_time = now - timedelta(hours=1)
    client = boto3.client('cloudwatch', 'us-east-1')
    response = client.get_metric_data(
        MetricDataQueries=queries,
        StartTime=start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        EndTime=now.strftime('%Y-%m-%dT%H:%M:%SZ')
    )

    results = response['MetricDataResults']

    scores = {}
    for r in results:
        team = r['Label']
        score = int(r['Values'][0]) if r['Values'] else 0
        scores[team] = score

    return scores

def get_scores_response():
    scores = get_scores()
    html = ''
    for team in scores:
        score = scores[team]
        html += f'<li class="list-group-item">{team}: {score}</li>'

    with open('scores.html', 'r') as file:
        data = file.read()

    t = string.Template(data)
    return get_cloudfront_response(t.substitute(scores=html))

    # Too bad this approach doesn't support number graphs!
    # with open('cw_metric_source.json', 'r') as file:
    #     widget_def = file.read()
    # response = client.get_metric_widget_image(MetricWidget=widget_def)
    # b64_bytes = base64.b64encode(response['MetricWidgetImage'])
    # return {
    #     'body': b64_bytes.decode(),
    #     'bodyEncoding': 'base64',
    #     'headers': {
    #         'content-type': [{
    #             'key': 'Content-Type',
    #             'value': 'image/png'
    #          }]
    #     },
    #     'status': '200'
    # }


def get_pick_team_response():
    scores = get_scores()

    team_list = ''
    for u in VALID_URIS:
        team = u.split('/')[-1]
        score = scores[team]

        query_params = ''
        if score > 0:
            # send them back to the last image they completed
            game_hash = game_hash_list[score - 1]
            game_id = game_ids[game_hash]
            query_params = f'?sequence={game_hash}&game_id={game_id}'

        team_list += f'<li class="list-group-item"><a href="{u}{query_params}">{team}</a></li>'

    params = {
        'version': VERSION,
        'teams': team_list
    }
    return get_response_from_template('pick.html', params)


def lambda_handler(event, context):
    global VERSION
    VERSION = context.function_version
    request = event['Records'][0]['cf']['request']
    uri = request['uri']

    if uri == '/hunt/inplainsight':
        return get_answers(request)

    if uri == '/hunt/score':
        return get_scores_response()

    if not uri in VALID_URIS:
        return get_pick_team_response()

    params = {
        'uri': uri,
        'sequence': game_hash_list[0],
        'game_num': 1,
        'game_count': len(game_hash_list)
    }

    querystring = request['querystring']

    if querystring:
        query_params = urllib.parse.parse_qs(querystring)
        sequence = query_params['sequence'][0]
        game_index = game_hash_list.index(sequence)
        game_num = game_index + 1

        # no game_id will be present if redirect from failed attempt

        if 'game_id' in query_params:
            game_id = query_params['game_id'][0]
        else:
            params['sequence'] = sequence
            params['game_num'] = game_num
            return get_response_from_template('clue.html', params)

        # verify combination of sequence / game_id

        if sequence in game_ids and game_ids[sequence] == game_id:
            team = uri.split('/')[-1]
            log_success(team, game_num)

            # find out if we are done, otherwise present next clue

            if game_index + 1 == len(game_hash_list):
                return get_response_from_template('congrats.html', params)
            else:
                params['sequence'] = game_hash_list[game_index + 1]
                params['game_num'] = game_num + 1
                return get_response_from_template('clue.html', params)
        else:
            params['sequence'] = sequence
            params['game_num'] = game_num
            return get_response_from_template('sorry.html', params)
    else:
        return get_response_from_template('clue.html', params)


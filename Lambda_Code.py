import base64
import json
import zlib
import datetime
import os
import boto3
from botocore.exceptions import ClientError

print('Loading function')


def lambda_handler(event, context):
    data = zlib.decompress(base64.b64decode(event['awslogs']['data']), 16+zlib.MAX_WBITS)
    data_json = json.loads(data)
    log_entire_json = json.loads(json.dumps(data_json["logEvents"], ensure_ascii=False))
    log_entire_len = len(log_entire_json)

    print(log_entire_json)

    for i in range(log_entire_len): 
        # ホスト名取得
        hostname = data_json['logGroup']
        
        # ログファイル名取得
        logname = data_json['logStream']
        
        # LogEvents取得
        log_json = json.loads(json.dumps(data_json["logEvents"][i], ensure_ascii=False))
        
        #UNIX時間→時刻/JST変換
        datetime_utc = log_json['timestamp'] / 1000.0
        datetime_utc = datetime.datetime.fromtimestamp(datetime_utc).strftime('%Y/%m/%d %H:%M:%S')
        datetime_utc = datetime.datetime.strptime(datetime_utc, '%Y/%m/%d %H:%M:%S')
        datetime_jst = datetime_utc + datetime.timedelta(hours = 9)
        
        # 件名整形
        subjectmsg = "【Alert】" + hostname + "_" + logname
        
        # 本文整形
        hostmsg = "■ホスト名:" + "\n" + hostname
        lognamemsg = "■ログファイル名:" + "\n" + logname
        timemsg = "■発生時刻:" + "\n" + str(datetime_jst)
        logmsg = "■ログ内容:" + "\n" + log_json['message']
        msg = hostmsg + "\n\n" + timemsg + "\n\n" + lognamemsg + "\n\n" + logmsg

        try:
            sns = boto3.client('sns')
    
            #SNS Publish
            publishResponse = sns.publish(
                TopicArn = os.environ['SNS_TOPIC_ARN'],
                Message = msg,
                Subject = subjectmsg
            )
    
        except Exception as e:
            print(e)
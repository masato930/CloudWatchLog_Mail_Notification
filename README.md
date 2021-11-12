# はじめに
CloudWatch Logsから対象のシステムログをメール通知する方法をアウトプットします。
今回はCloudWatch Logsのサブスクリプションフィルターを使用します。

※参考記事にあるクラスメソッドさんの記事を参考にしております。

<br>

# 構成
ログ送信の流れは以下の通りです。

**①EC2から CloudWatch Logs へログファイル出力**
**②サブスクリプションフィルターで特定文字列をマッチさせて Lambda 関数を起動**
**③Lambda 関数で該当メッセージを抽出、SNS 用に整形**
**④該当文字列が含まれた行を SNS で通知（今回はメール）**

<br>

![構成図](https://user-images.githubusercontent.com/61190510/141454953-92fd29a0-27bc-4314-9fd8-102e3d5ca339.png)

<br>


# 前提
- 作業用IAMユーザーにて作業を実施
- 今回は、AmazonLinuxの`/var/log/messages`からのログ抽出とします。
- CloudWatch logs上に既にOS上のログが出力されている状態になります。(OS上のCloudWatchエージェント設定については割愛とさせて頂きます。)
- CloudWatch Logsのロググループ名とログストリーム名は、事前に以下のように設定しております。

|  項目  |  内容  |  備考  |
| ---- | ---- | ---- |
|  ロググループ名  |  amalinux01  |  EC2のホスト名  |
|  ログストリーム名  |  /var/log/messages  |  監視したいログファイル名  |

- 監視したいEC2には、事前に`CloudWatchAgentAdminPolicy`をアタッチしたIAMロールを設定済み

<br>

# 今回のゴール

以下のような形でメール通知させる。


![mail](https://user-images.githubusercontent.com/61190510/141455009-6d93fa35-f3a5-497a-9b7b-88cf9f063c40.JPG)


# 全体の流れ

**①メール通知用SNSトピック作成**
**②Lambda関数の作成**
**③サブスクリプションフィルタの作成**
**④アラート発報試験**

# 作業手順

## ①メール通知用SNSトピック作成

**1.マネジメントコンソールよりSNSを開く。**

![① (1)](https://user-images.githubusercontent.com/61190510/141455037-26eff260-9df3-458b-81aa-ba4146a9a7ad.jpg)


**2.Amazon SNSの画面より「トピック」を開く。**

![① (2)](https://user-images.githubusercontent.com/61190510/141455053-b67d0a8d-3cd1-431c-bfac-025a553a5b72.jpg)


**3.トピック一覧より「トピックの作成」を開く。**

![① (3)](https://user-images.githubusercontent.com/61190510/141455066-c3ba1526-dbbf-48ff-af75-c0d2aa05f140.jpg)


**4.トピックの作成にて以下のように入力し、「トピックの作成」をクリック。**

|  項目  |  内容  |  備考  |
| ---- | ---- | ---- |
|  タイプ  |  スタンダード  |    |
|  名前  |  Alarm_Test  |  任意の名前でOK  |
|  表示名  |  空欄  |  入力は任意  |


![① (4)](https://user-images.githubusercontent.com/61190510/141455094-c271ebe1-6f08-4c3b-a7f2-7aaa75a0e4cb.jpg)

![① (5)](https://user-images.githubusercontent.com/61190510/141455103-ac2c15be-ba8d-4471-baf2-defc0245f781.jpg)


**5.トピックが作成されたことを確認。**

![① (6)](https://user-images.githubusercontent.com/61190510/141455120-8f2282bd-f5a8-4f08-97ae-88d4d858e45c.jpg)


**6.作成したトピックの画面にて「サブスクリプションの作成」をクリック。**

![① (7)](https://user-images.githubusercontent.com/61190510/141455130-571f9b74-b21c-471f-bdb2-e77afdb949ce.jpg)


**7.以下のように選択&入力し、「サブスクリプションの作成」をクリック。**

|  項目  |  内容  |  備考  |
| ---- | ---- | ---- |
|  トピックARN  |  該当トピックのARN  | そのままでOK   |
|  プロトコル |  Eメール  |  Eメールで通知するため  |
|  エンドポイント  |  通知したいEメールアドレス  |    |

<br>

![① (8)](https://user-images.githubusercontent.com/61190510/141455146-70688c6a-b8bf-41ec-b32b-34c6b6551948.jpg)

![① (9)](https://user-images.githubusercontent.com/61190510/141455182-06fb35bb-c33b-4044-a65f-a77ee8c279de.jpg)


**8.サブスクリプションが正常に作成できたことを確認。**

![① (10)](https://user-images.githubusercontent.com/61190510/141455221-392f2181-332f-4df4-9101-d86ce6de29ea.jpg)


**9.登録したメールアドレスに、以下件名でメールが届くので、メールの認証を実施する。**

```bash:件名
AWS Notification - Subscription Confirmation
```

![① (11)](https://user-images.githubusercontent.com/61190510/141455234-9119783e-4dc8-4956-bac2-dd84f780f4e2.jpg)


**10.再度、作成したトピック内のサブスクリプションを確認し、ステータスが「確認済み」になっていることを確認。**

![① (12)](https://user-images.githubusercontent.com/61190510/141455269-105294b4-c442-42a7-b363-b89cc7639698.jpg)


<br>

## ②Lambda関数の作成

**1.マネジメントコンソールよりLambdaを開く。**

![② (1)](https://user-images.githubusercontent.com/61190510/141455354-a4186011-bdeb-4825-8bfa-f8c0a53a37cd.jpg)


**2.Lambdaダッシュボードより「関数の作成」をクリック。**

![② (2)](https://user-images.githubusercontent.com/61190510/141455372-2e1770b1-618e-4883-9a1b-2149757f87a9.jpg)


**3.関数の作成の画面にて、「一から作成」にチェックを入れる。**

![② (3)](https://user-images.githubusercontent.com/61190510/141455382-ddad93f0-379c-43a8-8c38-b61d3c998612.jpg)


**4.基本的な情報の項目にて、以下のように選択し、「関数の作成」をクリック。**

|  項目  |  設定内容  |  備考  |
| ---- | ---- | ---- |
|  関数名  |  AlertCode  | 任意の名前を入力   |
|  ランタイム |  Python3.7  |    |
|  実行ロール  |  以下ポリシーがアタッチされているIAMロール<br>・CloudWatchLogsFullAccess<br>・AmazonSNSFullAccess  | 大きい権限を与えているため、実務で使用する場合はさらに制限が必要   |

![② (4)](https://user-images.githubusercontent.com/61190510/141455393-4766807b-b913-48ac-9ea6-dbd6d052ee59.jpg)


**5.関数が作成されることを確認。**

![② (5)](https://user-images.githubusercontent.com/61190510/141455410-4bd4ab2f-b737-48af-9e4e-c8c6103c5a52.JPG)

**6.下にスクロールし、「コード→lambda_function.py」と選択。以下コードをコピー&ペーストし、「Deploy」をクリック。**

![② (6)](https://user-images.githubusercontent.com/61190510/141455447-b0cf06e9-4d79-40cf-826a-948482b3f9b5.jpg)


```python:Lambda_Code.py
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
```

**7.コードのDeployが成功したことを確認。**

![② (7)](https://user-images.githubusercontent.com/61190510/141455515-3640aa2a-b341-4c66-827e-802bf0646508.JPG)


**8.「設定→一般設定→編集」と選択。**

![② (8)](https://user-images.githubusercontent.com/61190510/141455546-80586aca-6104-4466-8e83-6193438ca58c.jpg)


**9.タイムアウトを1分に設定し、「保存」をクリック。**

![② (9)](https://user-images.githubusercontent.com/61190510/141455570-980e1e5a-1697-4bac-8102-9cbda0ef559f.jpg)


**10.一般設定にてタイムアウトの値が「1分0秒」になっていることを確認。**

![② (10)](https://user-images.githubusercontent.com/61190510/141455590-c7c6b8fa-6b5b-4844-942d-d11649ef12e9.jpg)


**11.「環境変数→編集」と選択する。**

![② (11)](https://user-images.githubusercontent.com/61190510/141455595-45d9222d-07aa-4f20-a3c5-ed17a2a12bf4.jpg)


**12.以下の環境変数を追加し、「保存」をクリック。**

|  項目  |  設定内容  |  備考  |
| ---- | ---- | ---- |
|  キー  |  SNS_TOPIC_ARN  |  SNSのarnを格納する変数  |
|  値 |  arn:aws:sns:ap-northeast-1:+++++++++++++:Alerm_Test  |  「①メール通知用SNSトピック作成」にて作成したトピックのarn  |

![② (12)](https://user-images.githubusercontent.com/61190510/141455609-dac00edd-ab21-43ab-9197-0e4e86008088.jpg)


**13.環境変数が追加できたことを確認。**

![② (13)](https://user-images.githubusercontent.com/61190510/141455626-4c9c4764-7e58-4fa6-9524-6359bd43758d.jpg)

<br>

## ③サブスクリプションフィルタの作成

**1.マネジメントコンソールより「CloudWatch」を起動する。**

![③ (1)](https://user-images.githubusercontent.com/61190510/141455672-c2989600-b007-40a2-94a6-fd7be16a7be9.jpg)

**2.CloudWatch画面より「ロググループ」をクリックする。**

![③ (2)](https://user-images.githubusercontent.com/61190510/141455690-37a5e50a-411e-44da-b073-6f3181b254a1.jpg)


**3.今回の監視対象であるロググループをクリックする。**

![③ (3)](https://user-images.githubusercontent.com/61190510/141455705-08af266a-c3b6-4729-8479-cc62b38264e1.jpg)


**4.ロググループの画面より、「サブスクリプションフィルター」をクリックする。**

![③ (4)](https://user-images.githubusercontent.com/61190510/141455716-2847b54c-2d19-4719-96f9-b39e427f1ffa.jpg)


**5.サブスクリプションフィルター一覧の右側にある「作成」から「Lambdaサブスクリプションフィルターを作成」をクリックする。**

![③ (5)](https://user-images.githubusercontent.com/61190510/141455731-e7a34003-656c-48a8-97f0-18c32986f155.jpg)


**6.「②Lambda関数の作成」にて作成したLambda関数を選択する。**

![③ (6)](https://user-images.githubusercontent.com/61190510/141455742-1c5a3dfb-34e2-4a87-b9f2-cc06d44d7039.jpg)

**7.下にスクロールし、以下のように入力する。**

|  項目  |  設定内容  |  備考  |
| ---- | ---- | ---- |
|  ログの形式  |  JSON |    |
|  サブスクリプションフィルターのパターン | error  | フィルタリングしたい値を入力   |
|  サブスクリプションフィルター名 | 【ERROR】amalinux01(/var/log/messges)| 任意の名前を入力  |

![③ (7)](https://user-images.githubusercontent.com/61190510/141455759-bbbceae7-033c-43de-81f7-c41dae5bba87.jpg)


**8.パターンのテストを実施し問題ないことを確認後、「ストリーミングを開始」をクリックする。**

![③ (8)](https://user-images.githubusercontent.com/61190510/141455777-24a31570-c81a-4320-bc82-95036b785574.jpg)


**9.サブスクリプションフィルターが作成できたことを確認。**

![③ (9)](https://user-images.githubusercontent.com/61190510/141455798-ebd1dd6c-fbe4-4388-9390-7ef553b82809.jpg)


※Lambdaの「設定→トリガー」の部分でも、サブスクリプションフィルターが追加されたことを確認可能

![③ (10)](https://user-images.githubusercontent.com/61190510/141455823-65e119a6-c45d-44ca-a28f-770302609bb1.jpg)

<br>

## ④アラート発報試験

**1.監視対象のEC2へログインし、以下コマンドを実行する。**
※今回は、AmazonLinux2を使用しています。

```bash:コマンド
logger -p user.err -t ERROR "プログラムでエラーが発生しました"
```

**2.`/var/log/messages`にログが追記されていることを確認。**

```bash:コマンド
sudo tail -1 /var/log/messages
```

```bash:コマンド実行例
[ec2-user@ip-10-0-0-204 ~]$ sudo tail -1 /var/log/messages
Aug  1 15:42:41 ip-10-0-0-204 ERROR: プログラムでエラーが発生しました
[ec2-user@ip-10-0-0-204 ~]$
```

**3.少々待つと以下内容のメールが受信される。**

![④ (1)](https://user-images.githubusercontent.com/61190510/141456128-45afba2f-f68e-4f6c-99aa-fe7a49e01a06.JPG)


※Lambdaの対象関数内の「モニタリング」を確認すると、実行ログを確認することが可能。

![④ (2)](https://user-images.githubusercontent.com/61190510/141456143-e2645908-f555-47fd-9978-8c58949e203e.JPG)

![④ (3)](https://user-images.githubusercontent.com/61190510/141456156-c3aea0e8-b978-45ad-aad2-4fcd5e318b04.JPG)


<br>

# 参考記事
[CloudWatch Logs を文字列検知してログ内容をメールを送信してみた サブスクリプションフィルター版](https://dev.classmethod.jp/articles/notification_cloudwatchlogs_subscriptoinfilter/)


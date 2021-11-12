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

![](https://storage.googleapis.com/zenn-user-upload/601d490c0ac32da293f6a933.png)

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

![](https://storage.googleapis.com/zenn-user-upload/2ea837c8a744837e291544d4.jpg)


# 全体の流れ

**①メール通知用SNSトピック作成**
**②Lambda関数の作成**
**③サブスクリプションフィルタの作成**
**④アラート発報試験**

# 作業手順

## ①メール通知用SNSトピック作成

**1.マネジメントコンソールよりSNSを開く。**

![](https://storage.googleapis.com/zenn-user-upload/5d19850eecd931cbba3de322.jpg)

**2.Amazon SNSの画面より「トピック」を開く。**

![](https://storage.googleapis.com/zenn-user-upload/f55a8ccf9fa4b4fd6ec78abd.jpg)

**3.トピック一覧より「トピックの作成」を開く。**

![](https://storage.googleapis.com/zenn-user-upload/add8bb7b0410917d47cae3dc.jpg)

**4.トピックの作成にて以下のように入力し、「トピックの作成」をクリック。**

|  項目  |  内容  |  備考  |
| ---- | ---- | ---- |
|  タイプ  |  スタンダード  |    |
|  名前  |  Alarm_Test  |  任意の名前でOK  |
|  表示名  |  空欄  |  入力は任意  |

![](https://storage.googleapis.com/zenn-user-upload/b579d82da098f06365db8e63.jpg)

![](https://storage.googleapis.com/zenn-user-upload/83cf2d54b011444d8dd88e55.jpg)

**5.トピックが作成されたことを確認。**

![](https://storage.googleapis.com/zenn-user-upload/3e710b5acdb8edd6297d8d51.jpg)

**6.作成したトピックの画面にて「サブスクリプションの作成」をクリック。**

![](https://storage.googleapis.com/zenn-user-upload/4c501192f2142fbecb5c6b5a.jpg)

**7.以下のように選択&入力し、「サブスクリプションの作成」をクリック。**

|  項目  |  内容  |  備考  |
| ---- | ---- | ---- |
|  トピックARN  |  該当トピックのARN  | そのままでOK   |
|  プロトコル |  Eメール  |  Eメールで通知するため  |
|  エンドポイント  |  通知したいEメールアドレス  |    |

![](https://storage.googleapis.com/zenn-user-upload/d43b9ec511cfd900d5960523.jpg)

![](https://storage.googleapis.com/zenn-user-upload/9fc155a6de9329f0a85a6b38.jpg)

**8.サブスクリプションが正常に作成できたことを確認。**

![](https://storage.googleapis.com/zenn-user-upload/89e8614816577aba2e752fa3.jpg)

**9.登録したメールアドレスに、以下件名でメールが届くので、メールの認証を実施する。**

```bash:件名
AWS Notification - Subscription Confirmation
```

![](https://storage.googleapis.com/zenn-user-upload/e7424dea7040ce51f53ffe3f.jpg)

**10.再度、作成したトピック内のサブスクリプションを確認し、ステータスが「確認済み」になっていることを確認。**

![](https://storage.googleapis.com/zenn-user-upload/b62b74a88d00f144bc8a1772.jpg)

<br>

## ②Lambda関数の作成

**1.マネジメントコンソールよりLambdaを開く。**

![](https://storage.googleapis.com/zenn-user-upload/7141dadda1aec5c02b173471.jpg)

**2.Lambdaダッシュボードより「関数の作成」をクリック。**

![](https://storage.googleapis.com/zenn-user-upload/ffab897b8fb2a9aff529b31a.jpg)

**3.関数の作成の画面にて、「一から作成」にチェックを入れる。**

![](https://storage.googleapis.com/zenn-user-upload/aedc45a725aa1c805da375e0.jpg)

**4.基本的な情報の項目にて、以下のように選択し、「関数の作成」をクリック。**

|  項目  |  設定内容  |  備考  |
| ---- | ---- | ---- |
|  関数名  |  AlertCode  | 任意の名前を入力   |
|  ランタイム |  Python3.7  |    |
|  実行ロール  |  以下ポリシーがアタッチされているIAMロール<br>・CloudWatchLogsFullAccess<br>・AmazonSNSFullAccess  | 大きい権限を与えているため、実務で使用する場合はさらに制限が必要   |

![](https://storage.googleapis.com/zenn-user-upload/d55d3876ae8f9962773fffa1.jpg)

**5.関数が作成されることを確認。**

![](https://storage.googleapis.com/zenn-user-upload/b2429a1eeebeb5622560f4ef.jpg)

**6.下にスクロールし、「コード→lambda_function.py」と選択。以下コードをコピー&ペーストし、「Deploy」をクリック。**

![](https://storage.googleapis.com/zenn-user-upload/1d9afc3019e48254b48a3962.jpg)

```python:コード
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

![](https://storage.googleapis.com/zenn-user-upload/d233c71329beabc7ee749371.jpg)

**8.「設定→一般設定→編集」と選択。**

![](https://storage.googleapis.com/zenn-user-upload/1bed10a257a01daf88bea0d1.jpg)

**9.タイムアウトを1分に設定し、「保存」をクリック。**

![](https://storage.googleapis.com/zenn-user-upload/c177740b0e822b0e622c8894.jpg)

**10.一般設定にてタイムアウトの値が「1分0秒」になっていることを確認。**

![](https://storage.googleapis.com/zenn-user-upload/a096ecd3b7ded3d9401dc999.jpg)

**11.「環境変数→編集」と選択する。**

![](https://storage.googleapis.com/zenn-user-upload/e5cc0f41608a03e77521b563.jpg)

**12.以下の環境変数を追加し、「保存」をクリック。**

|  項目  |  設定内容  |  備考  |
| ---- | ---- | ---- |
|  キー  |  SNS_TOPIC_ARN  |  SNSのarnを格納する変数  |
|  値 |  arn:aws:sns:ap-northeast-1:+++++++++++++:Alerm_Test  |  「①メール通知用SNSトピック作成」にて作成したトピックのarn  |

![](https://storage.googleapis.com/zenn-user-upload/b579ebb111ff1fe8fd20ae67.jpg)

**13.環境変数が追加できたことを確認。**

![](https://storage.googleapis.com/zenn-user-upload/e4921bf5a33e404926d52f6c.jpg)

## ③サブスクリプションフィルタの作成

**1.マネジメントコンソールより「CloudWatch」を起動する。**

![](https://storage.googleapis.com/zenn-user-upload/796689781c8b6889fe5f9b6a.jpg)

**2.CloudWatch画面より「ロググループ」をクリックする。**

![](https://storage.googleapis.com/zenn-user-upload/218f0c16d12634c1ef7d757f.jpg)

**3.今回の監視対象であるロググループをクリックする。**

![](https://storage.googleapis.com/zenn-user-upload/fcb17f58ba0e2ca8df292269.jpg)

**4.ロググループの画面より、「サブスクリプションフィルター」をクリックする。**

![](https://storage.googleapis.com/zenn-user-upload/f7eb8e97dd0ff906d9d6a61b.jpg)

**5.サブスクリプションフィルター一覧の右側にある「作成」から「Lambdaサブスクリプションフィルターを作成」をクリックする。**

![](https://storage.googleapis.com/zenn-user-upload/3419bf0e664a8a476b0c9619.jpg)

**6.「②Lambda関数の作成」にて作成したLambda関数を選択する。**

![](https://storage.googleapis.com/zenn-user-upload/dd4ca4d8f6a572ee17035880.jpg)

**7.下にスクロールし、以下のように入力する。**

|  項目  |  設定内容  |  備考  |
| ---- | ---- | ---- |
|  ログの形式  |  JSON |    |
|  サブスクリプションフィルターのパターン | error  | フィルタリングしたい値を入力   |
|  サブスクリプションフィルター名 | 【ERROR】amalinux01(/var/log/messges)| 任意の名前を入力  |

![](https://storage.googleapis.com/zenn-user-upload/4c00ec1f36ff549399f99668.jpg)

**8.パターンのテストを実施し問題ないことを確認後、「ストリーミングを開始」をクリックする。**

![](https://storage.googleapis.com/zenn-user-upload/e1cb98397638817dafce4417.jpg)

**9.サブスクリプションフィルターが作成できたことを確認。**

![](https://storage.googleapis.com/zenn-user-upload/9eab38b7fbccbb3025b860c4.jpg)

※Lambdaの「設定→トリガー」の部分でも、サブスクリプションフィルターが追加されたことを確認可能

![](https://storage.googleapis.com/zenn-user-upload/1e43a9ab55b1ae3db69f68d4.jpg)

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

![](https://storage.googleapis.com/zenn-user-upload/2ea837c8a744837e291544d4.jpg)

※Lambdaの対象関数内の「モニタリング」を確認すると、実行ログを確認することが可能。

![](https://storage.googleapis.com/zenn-user-upload/0b8edb8595da1775364c66bd.jpg)

![](https://storage.googleapis.com/zenn-user-upload/304814f7fc60e020623168be.jpg)

<br>

# 参考記事
[CloudWatch Logs を文字列検知してログ内容をメールを送信してみた サブスクリプションフィルター版](https://dev.classmethod.jp/articles/notification_cloudwatchlogs_subscriptoinfilter/)


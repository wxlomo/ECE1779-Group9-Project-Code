import time
import datetime
from dateutil.tz import tzutc
import boto3
instances={}


db_config = {
    'user': 'root',
    'password': 'ece1779pass',
    'host': '127.0.0.1',
    'database': 'gallery'
}
awsKey={
    'aws_access_key_id' : 'AKIA3NQ4GILKF3U7HZWT',
    'aws_secret_access_key' : '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'
}
VPCID='vpc-042054f0f945d031c'
SubnetID='subnet-0c43635379007a839'
SecurityGroupID='sg-0bd84a8e573f6d497'
ami = "ami-080ff70d8f5b80ba5"

def refreshStateandIP(client):
        """
            Refresh instacne with current state from AWS.
        """
        # client = boto3.client('ec2', 
        #                     region_name='us-east-1',
        #                     aws_access_key_id=awsKey.aws_access_key_id,
        #                     aws_secret_access_key=awsKey.aws_secret_access_key)
        response = client.describe_instances()
        instances.clear()


        # print(response)
        for i in response["Reservations"]:
            if ami == i["Instances"][0]["ImageId"] and "Tags" in i["Instances"][0] and i["Instances"][0]["Tags"][0]["Value"].__contains__("ECE1779_A2_Memcache") and i["Instances"][0]["State"]["Name"] != 'terminated'and i["Instances"][0]["State"]["Name"] != 'shutting-down':
                
                memcacheName = i["Instances"][0]["Tags"][0]["Value"]
                memcacheNum = int(memcacheName[-1])
                

                instances[str(memcacheNum)] = {"Name": memcacheName,
                                                        "Status": i['Instances'][0]["State"]["Name"],
                                                        "instanceID": i['Instances'][0]['InstanceId'],
                                                        "amiID": ami,
                                                        "Number": memcacheNum,
                                                        "PublicIP": ""}

                if "PublicIpAddress" in i["Instances"][0].keys() and i["Instances"][0]["PublicIpAddress"]:
                    instances[str(memcacheNum)]["PublicIP"] = i["Instances"][0]["PublicIpAddress"]

        
        return True
        

def start_ec2_instance():
        """
            MaxCount=1, # Keep the max count to 1, unless you have a requirement to increase it
            InstanceType="t2.micro", # Change it as per your need, But use the Free tier one
            KeyName="ECE1779_A2_public"
            :return: Creates the EC2 instance.
        """

        client = boto3.client('ec2', 
                            region_name='us-east-1',
                            aws_access_key_id=awsKey.aws_access_key_id,
                            aws_secret_access_key=awsKey.aws_secret_access_key)
        if not refreshStateandIP(client):
            print("Fail retirving state form aws. Abandoning operation.")
            return False
        # Start exist instances:
        available = False
        for instance in instances.values():
            if instance["Status"]=='stopped':
                available=True
                break
        if (available):
            print("starting EC2 instance...")
            client.start_instances(InstanceIds=[instance["instanceID"]])
            return True
        # Create instance if no available instance and have not reach maximum memcaches (8):
        elif (len(instances) < 8):
            print("Creating EC2 instance...")
            
            # Check what is the latest num

            number = 0
            memcacheName = ("ECE1779_A2_Memcache_" +
                            str(0))
            for i in range(8):
                if str(i) not in instances.keys():
                    break
                
            number = i
            memcacheName = ("ECE1779_A2_Memcache_" +
                            str(i))


            new = client.run_instances(

                ImageId=ami,
                MinCount=1,
                MaxCount=1,
                InstanceType="t2.micro",
                KeyName="ECE1779_A2_public",
                SecurityGroupIds=[SecurityGroupID],
                SubnetId=SubnetID,
                TagSpecifications=[{'ResourceType': 'instance',
                                    'Tags': [
                                        {
                                            'Key': 'Name',
                                            'Value': memcacheName
                                        },
                                    ]
                                    }]

            )
            

            instances[str(number)] = {"Name": memcacheName,
                                              "Status": new['Instances'][0]["State"]["Name"],
                                              "instanceID": new['Instances'][0]['InstanceId'],
                                              "amiID": ami,
                                              "Number": number,
                                              "PublicIP": ""}
            return True
        else:
            print("Already has 8 memcaches. ")
            return False


def stop_ec2_instance():
        """
            Stop memcache with the LARGEST number.
            Note that you should wait for some time for the memcache EC2 to shutdown before it shows up.
        """
        if instances:
            client = boto3.client('ec2', 
                            region_name='us-east-1',
                            aws_access_key_id=awsKey.aws_access_key_id,
                            aws_secret_access_key=awsKey.aws_secret_access_key)
            if not refreshStateandIP(client):
                print("Fail retirving state form aws. Abandoning operation.")
                return "Fail retirving state form aws. Abandoning operation."
            # Check what is the last num
            id = -1
            for instance in instances.values():
                if instance["Status"]=='running':
                    id=instance["instanceID"]
                    break
            if id !=-1:
                client.stop_instances(InstanceIds=[id])
                return "OK"
            else:
                print("No running memcache instances")
                return "ERROR! No running memcache instances"
        return "ERROR! No memcache instances."

def get_all_ip():
        """Returns all known IPs of all EC2 memcaches for frontend to use."""
        ipList = []
        if not refreshStateandIP():
            print("Fail retirving state form aws. Abandoning operation.")
            return
        if instances:
            for instance in instances.values():
                if instance["PublicIP"] != "":
                    ipList.append(instance["PublicIP"])
        return ipList





def getAggregateMissRate1mins(instances: list, intervals=60, period=60):
    client = boto3.client('cloudwatch', 
                            region_name='us-east-1',
                            aws_access_key_id=awsKey.aws_access_key_id,
                            aws_secret_access_key=awsKey.aws_secret_access_key)
    startTime = datetime.datetime.utcnow() - datetime.timedelta(seconds=intervals)
    endTime = datetime.datetime.utcnow()
    miss = 0
    total= 0
    for i in instances:
        
        miss+=client.get_metric_statistics(
                Namespace='ece1779/memcache',
                MetricName='miss',
                Dimensions=[{
                        "Name": "instance",
                        "Value": i
                    }],
                StartTime = startTime,
                EndTime = endTime,
                Period=period,
                Statistics=['Sum'],
                Unit='Count',
                )['Datapoints']['Sum']
        
        total+=client.get_metric_statistics(
                Namespace='ece1779/memcache',
                MetricName='total',
                Dimensions=[{
                        "Name": "instance",
                        "Value": i
                    }],
                StartTime = startTime,
                EndTime = endTime,
                Period=period,
                Statistics=['Sum'],
                Unit='Count',
                )['Datapoints']['Sum']
            
    return miss/total
    
    
def getAggregateStat30Mins(instances: list):
    numberItems=[]
    currentSize=[]
    totalRequests=[]
    missRate=[]
    hitRate=[]
    client = boto3.client('cloudwatch', 
                        region_name='us-east-1',
                        aws_access_key_id=awsKey.aws_access_key_id,
                        aws_secret_access_key=awsKey.aws_secret_access_key)
    now=datetime.datetime.utcnow()
    for i in range (30,1,-1):
        startTime = now - datetime.timedelta(minutes=i)
        endTime = now - datetime.timedelta(minutes=i-1)
        miss = 0
        total= 0
        for i in instances:
            
            miss+=client.get_metric_statistics(
                    Namespace='ece1779/memcache',
                    MetricName='miss',
                    Dimensions=[{
                            "Name": "instance",
                            "Value": i
                        }],
                    StartTime = startTime,
                    EndTime = endTime,
                    Period=60,
                    Statistics=['Sum'],
                    Unit='Count',
                    )['Datapoints']['Sum']
            
            total+=client.get_metric_statistics(
                    Namespace='ece1779/memcache',
                    MetricName='total',
                    Dimensions=[{
                            "Name": "instance",
                            "Value": i
                        }],
                    StartTime = startTime,
                    EndTime = endTime,
                    Period=60,
                    Statistics=['Sum'],
                    Unit='Count',
                    )['Datapoints']['Sum']
            
            numItem=client.get_metric_statistics(
                    Namespace='ece1779/memcache',
                    MetricName='numberItems',
                    Dimensions=[{
                            "Name": "instance",
                            "Value": i
                        }],
                    StartTime = startTime,
                    EndTime = endTime,
                    Period=60,
                    Statistics=['Average'],
                    Unit='Count',
                    )['Datapoints']['Average']
            
            size=client.get_metric_statistics(
                    Namespace='ece1779/memcache',
                    MetricName='currentSize',
                    Dimensions=[{
                            "Name": "instance",
                            "Value": i
                        }],
                    StartTime = startTime,
                    EndTime = endTime,
                    Period=60,
                    Statistics=['Average'],
                    Unit='Count',
                    )['Datapoints']['Average']
                
        missRate.append(miss/total)
        hitRate.append(1-miss/total)
        totalRequests.append(total)
        numberItems.append(numItem)
        currentSize.append(size)
    return [numberItems, currentSize, totalRequests, missRate, hitRate]
          

        

    
    
    
    
    

        
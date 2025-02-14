# Live Zoom Transcription Bot

This is a Zoom bot based on the [Python Zoom SDK bindings](https://github.com/noah-duncan/py-zoom-meeting-sdk) by Noah Duncan. It takes the audio from Zoom meetings and sends it to OpenAI for transcription.

## Deployment

Deploy to AWS ESC with fargate task.

## Running the development program

- Run `docker compose run --rm develop`

### Build and test run docker image

- Run `docker build -t TAG .`
- Run `docker run TAG`

## ECR

### Setting up ECR

Create a private repository in ECR. For my example, I named it `zoom-bot`.

### Push image to ECR

Click view push commands and run the commands. (This may take a while to push)

## ECS

### Setting up fargate task definition

Launch type: `Fargate`  
Operating system/Architecture: `Linux/X86_64`

**Container - 1**:  
Name: `zoom-bot`  
Image: `YOUR_IMAGE_URI`

Add Environment variables:
```
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
ZOOM_CLIENT_ID=YOUR_ZOOM_CLIENT_ID
ZOOM_CLIENT_SECRET=YOUR_ZOOM_CLIENT_SECRET
```

### Setting up ECS cluster

Name: `zoom-bot`  
Infrastructure: `Fargate`

### Run the task

You can either run the task manually or set up a Lambda function to run the task. Note that you need to set an environment variable with the JOIN_URL. 

Below is an example of a Lambda function that runs the task using python:

```
import boto3

cluster = "YOUR_CLUSTER_ARN"
task_definition = "YOUR_TASK_DEFINITION_ARN"
subnets = ["YOUR_SUBNET_ARN_1", "YOUR_SUBNET_ARN_2"]
security_groups = ["YOUR_SECURITY_GROUP_ARN_1"]
join_url = "YOUR_JOIN_URL"

# Initialize ECS client
ecs_client = boto3.client('ecs')

# Run ECS task
run_response = ecs_client.run_task(
    cluster=cluster,
    taskDefinition=task_definition,
    launchType="FARGATE",
    networkConfiguration={
        "awsvpcConfiguration": {
            "subnets": subnets,
            "securityGroups": security_groups,
            "assignPublicIp": "ENABLED"
        }
    },
    overrides={
        "containerOverrides": [
            {
                "name": "zoom-bot",
                "environment": [
                    {"name": "JOIN_URL", "value": join_url},
                ]
            }
        ]
    },
    count=1
)
```

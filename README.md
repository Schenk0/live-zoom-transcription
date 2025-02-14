# Live Zoom Transcription Bot

## Deployment

Deploy to AWS ESC with fargate task.


### Build and test run docker image

- Run `docker build -t TAG .`
- Run `docker run TAG`

### Push image to ECR

```
aws ecr get-login-password --region us-west-1 | docker login --username AWS --password-stdin 533267296380.dkr.ecr.us-west-1.amazonaws.com
docker build -t zoom-bot .
docker tag zoom-bot:latest 533267296380.dkr.ecr.us-west-1.amazonaws.com/zoom-bot:latest
docker push 533267296380.dkr.ecr.us-west-1.amazonaws.com/zoom-bot:latest
```

## Running the development program

- Run `docker compose run --rm develop`
- Run `python src/main.py`
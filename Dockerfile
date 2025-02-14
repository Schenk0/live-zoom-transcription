FROM --platform=linux/amd64 ubuntu:22.04 AS base

SHELL ["/bin/bash", "-c"]

ENV project=zoom-bot
ENV cwd=/tmp/$project

WORKDIR $cwd

ARG DEBIAN_FRONTEND=noninteractive

# Install Python
RUN apt-get update && apt-get install -y python3-pip

# Install ALSA
RUN apt-get install -y libasound2 libasound2-plugins alsa alsa-utils alsa-oss

# Install Pulseaudio
RUN apt-get install -y  pulseaudio pulseaudio-utils ffmpeg

# Install Linux Kernel Dev
RUN apt-get update && apt-get install -y linux-libc-dev

# Install Ctags
RUN apt-get update && apt-get install -y universal-ctags

# Alias python3 to python
RUN ln -s /usr/bin/python3 /usr/bin/python

FROM base AS deps

# Install requirements.txt
COPY requirements.txt .
RUN pip install -r requirements.txt

ENV TINI_VERSION=v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

WORKDIR /opt

FROM deps AS build

WORKDIR $cwd
COPY . .

#CMD ["/bin/bash"]

RUN chmod +x /tini

ENTRYPOINT ["/tini", "--"]
CMD ["python", "src/main.py"]

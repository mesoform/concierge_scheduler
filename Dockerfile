FROM python:3
COPY docker-entrypoint.sh /scripts/docker-entrypoint.sh
COPY . /concierge_scheduler
RUN ["chmod", "+x", "/scripts/docker-entrypoint.sh"]
RUN pip install pyzabbix
RUN pip install google-auth
RUN pip install google-cloud-storage
ENTRYPOINT ["/scripts/docker-entrypoint.sh"]
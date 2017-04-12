#!/usr/bin/env bash

# Scale up by 1
echo "scale Consul servers from 3 to 4"
bash ../concierge_scheduler/concierge_scheduler.sh scale_up consul 3 1
echo

# Scale up by 3
echo "scale Consul servers from 3 to 6"
bash ../concierge_scheduler/concierge_scheduler.sh scale_up consul 3 3
echo

# Scale down by 1
echo "scale MyApp servers from 4 to 3"
bash ../concierge_scheduler/concierge_scheduler.sh scale_down myapp 4 1
echo

# Scale down by 2
echo "scale MyApp servers from 6 to 4"
bash ../concierge_scheduler/concierge_scheduler.sh scale_down consul 6 2
echo -e "\n\n"

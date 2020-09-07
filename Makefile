
requirements:
	@pipreqs --print mlcode | sed 's/==/>=/' > requirements.txt

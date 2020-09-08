
requirements:
	@pipreqs --print nlpready | sed 's/==/>=/' > requirements.txt

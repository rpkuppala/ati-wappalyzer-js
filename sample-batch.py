from cgitb import reset
from auth_utils import GetAuthTokenCH
from aiochclient import ChClient
from aiohttp import ClientSession
from dotenv import load_dotenv
from httpx import Timeout
import asyncio
import aiohttp
import httpx
import urllib.parse
import json
import os
import pymysql

query = "SELECT DISTINCT t.`prov.ac` as acc, t.`prov.service_app_id` as appId, t.`request.protocol` as proto, t.request_host as host, t.`request.port` as port, t.`request.url` as url, count(*) as cnt FROM waf.traffic t WHERE (t.`prov.ac` > 13369) AND	(t.`timestamp` >= now() - interval 1 day) and (t.`is_enrichment.is_ajax_request` = 0) and (t.`is_enrichment.is_static_resource_request`=0) and (t.`request.method` = 'GET')	and (t.`response.resp_code`=200) and (t.`response.resp_size` > 0) GROUP BY acc , appId, proto, host, port, url ORDER BY	acc, appId,	cnt DESC LIMIT 1 BY acc, appId"
load_dotenv()
BRS_SVC_URL = os.getenv('BRS_SVC_URL')
ATI_WAPPALYZER_URL = os.getenv('ATI_WAPPALYZER_URL')


async def main():
    keys = GetAuthTokenCH.get_auth_keys("prod")
    # print(keys)
    async with ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as s:
        client = ChClient(s, url=BRS_SVC_URL,
                          user=keys['Key'], password=keys['Token'], database='waf')
        assert await client.is_alive()  # returns True if connection is Ok
        all_rows = await client.fetch(query)
        print('Total Apps to process:'+str(len(all_rows)))
        conn = pymysql.connect(host=os.getenv('DB_ARGUS_HOST'), user=os.getenv(
            'DB_ARGUS_USERNAME'), password=os.getenv('DB_ARGUS_PASSWORD'), charset='utf8', db=os.getenv('DB_ARGUS_NAME'))
        cur = conn.cursor()
        # with open("my_file.json", "a", encoding="utf-8") as f:
        with open("test_stats.sql", "a", encoding="utf-8") as f:
            try:
                for row in all_rows:
                    proto = int(row['proto'])
                    url = row['host']+row['url']
                    if proto == 0:
                        url = 'http://'+url
                    else:
                        url = 'https://'+url
                    print('http://localhost:8080/' +
                          urllib.parse.quote_plus(url))
                    res = httpx.get(url=ATI_WAPPALYZER_URL+urllib.parse.quote_plus(
                        url), verify=False, timeout=Timeout(timeout=120.0))
                    if res.text:
                        data = {
                            "acc": row['acc'], "app": row['appId'],  "data": json.loads(res.text)}
                        raw_str = json.dumps(data)
                        loaded_po = json.loads(raw_str)
                        techs = loaded_po['data']
                        for tech in techs['technologies']:
                            print(tech)
                            statement = ("INSERT INTO test.app_categories(account, appId, slug, description, confidence, version, icon, website, cpe, category) VALUES(" +
                                         str(data['acc'])+",'"+data['app']+"','"+tech['slug']+"','" + (tech.get('description') if tech.get('description') else '') + "'," + str(tech['confidence'])+",'" +
                                         (tech.get('version') if tech.get('version') else '') + "','"+(tech.get('icon') if tech.get('icon') else '')+"','"+tech.get('website')+"','" + (tech.get('cpe') if tech.get('cpe') else '') + "',")
                            for categ in tech['categories']:
                                stmt = statement+str(categ['id'])+");"
                                #print(stmt)
                                sql = """INSERT INTO `app_categories` (account, appId, slug, description, confidence, version, icon, website, cpe, category)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                                """
                                cur.execute(sql, (data['acc'], data['app'], tech['slug'], (tech.get(
                                    'description') if tech.get('description') else ''), tech['confidence'], (tech.get('version') if tech.get('version') else ''), (tech.get('icon') if tech.get('icon') else ''), tech.get('website'), (tech.get('cpe') if tech.get('cpe') else ''), categ['id']))
                                conn.commit()
                                f.write(stmt)
            except Exception as e:
                print('Error while processing::' + str(e))
                # print(res.text)
            f.close()
        conn.close()
        print('Processing is done.')
        return 1

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()

# if __name__ == "__main__":
#    main()

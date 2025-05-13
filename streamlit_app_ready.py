import streamlit as st
import pandas as pd
import requests
import json

def get_crypto_data(crypto,fiat):
    headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': st.secrets["API_KEY"],
    }

    response = requests.get(f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?symbol={crypto}&convert={fiat}"
                            ,headers=headers)

    if response.status_code in [200,201]:
        print("success")
        print(json.dumps(response.json(),indent=4))
        data = pd.DataFrame(response.json()["data"][crypto][0]["quote"][fiat]
                        ,index=["BTC"])
        data_percentage_change = data[["percent_change_1h"
                                ,"percent_change_24h"
                                ,"percent_change_7d"
                                ,"percent_change_30d"
                                ,"percent_change_60d"
                                ,"percent_change_90d"]]
        data_percentage_change.columns = ["1h","24h","7d","30d","60d","90d"]
        data_percentage_change_transpose = data_percentage_change.T
        st.line_chart(data_percentage_change_transpose)
    else:
        print(f"error {response.status_code} with error: {response.text}")

st.write("# Crypto price visualizer")
col1,col2 = st.columns(2)

crypto_selected = col1.text_input("Enter crypto")
currency_selected = col2.text_input("Enter currency")

st.write(f"**{crypto_selected}:{currency_selected}**")

if st.button("visualize"):
    get_crypto_data(crypto_selected,currency_selected)


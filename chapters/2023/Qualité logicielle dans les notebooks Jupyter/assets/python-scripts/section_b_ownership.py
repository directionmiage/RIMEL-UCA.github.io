#!/usr/bin/env python
# coding: utf-8

# # Passive ownership and flows
# ## Why it matters
# 
# - Passive management has seen unprecedented growth in the past 10-15 years<br><img src="images/ST_passive.png"><br>Source: Sushko, V., and G. Turner (2018) The implications of passive investing for securities markets, BIS Quarterly Review, March 2018, 113–131.
# - Academics have found that institutional ownership in general tends to be positively associated with security return volatility (Sias, 1996)
# - Ben-David et al. (2018) find that this is particularly true for ETFs
# 
# **The main mechanism:**
# - Liquidity shocks (i.e. inflows and outflows) that affect the fund propagate to the underlying securities, thereby increasing volatility
# - This mechanism is stronger in the case of passive funds because of the limited discretionality in the timing and direction of trades
# 
# **Key results of our work:**
# - In our paper, <a href="https://marquee.gs.com/content/markets/en/2020/10/28/734dc59c-b03b-4793-9f56-98ec5ebca4d8.html">"The Shift from Active to Passive" (July 2019)</a>, we find that passively held stocks tend to be more volatile after correcting for other stock characteristics
# - The effect of passive ownership on volatility is concentrated at the end of the continuous trading session and at the Close<br><img src="images/Impact_hourly_sub.png"><br>Source: GS Global Markets Division.
# - The effect of passive inflows and outflows is similarly concentrated around the Close<br><img src="images/Impact_hourly_sub_flow.png"><br>Source: GS Global Markets Division.
# - This is arguably due to the concentration of portfolio trades in the order flow during that phase
# - We also detect differences in the impact of passive investing between US and European markets due to the different design of the closing auction
# 
# **Passive ownership and the March 2020 selloff**
# - In our paper, <a href="https://marquee.gs.com/content/markets/en/2020/10/28/e251979b-cc31-49c6-bf8f-f585c6f22aa7.html">"Dissecting the Viral Selloff" (April 2020)</a>, we group stocks by their level of passive ETF ownership and compare the percentage increase in volatility between January and March 2020<br><img src="images/vol_pass_own_US.png"><img src="images/vol_pass_own_Europe.png"><br>Source: GS Global Markets Division.
# 
# - Stocks widely held by ETFs have experienced larger volatility increases, both in the US and in Europe
# - The result holds true after correcting for other effects, including sector, country, size and liquidity
# 
# ## Measuring passive ownership and flows
# - Starting from fund-level data, we produce stock-level indicators by using the latest information on holdings and flows
# - Raw ownership ratios:
# \begin{equation}
# PassETFRatio_{i}=\frac{\sum_{j\in F_{PassETF}}w_{ij}AuM_{j}}{MktCap_{i}}
# \label{passETFratio}
# \end{equation}
# where $w_{ij}$ is the weight of stock $i$ in fund $j$, $AuM_{j}$ is the total value of fund $j$'s holdings, $F_{PassETF}$ the set of passive ETFs and $MktCap_{i}$ is 
# the market capitalisation in US dollars of stock $i$
# - Building on our research, we carry out a series of cross-sectional normalisations and adjustments to make the scores comparable across regions and over time
# - Scores are normalised between -3 and 3. Higher scores indicate a higher level of passive ownership
# - Similarly, for flow scores a higher score indicates stronger inflows to passive funds holding the stock
# 

# #### Import libraries

# In[ ]:


import pandas as pd
from gs_quant.markets.securities import SecurityMaster, AssetIdentifier
from gs_quant.session import GsSession
from gs_quant.data import Dataset
import datetime as dt
import matplotlib.pyplot as plt

# #### Supply credentials

# In[ ]:


# external users should substitute their client id and secret; please skip this step if using internal jupyterhub
GsSession.use(Environment.PROD, client_id=client_id, client_secret=client_secret, scopes=('read_product_data',))

# ## Load basket of stocks from text file

# In[ ]:


# load data from csv
ptf_df = pd.read_csv('trade_list_world.csv')
ptf_df = ptf_df.rename(columns={'Symbol': 'SEDOL', 'Trade Value ($)': 'Value'})
ptf_df

# ## Map identifiers

# In[ ]:


# load Marquee identifiers and Bloomberg Ids
identifiers_df = {}
for sedol_id in ptf_df.SEDOL:
    identifiers_df[sedol_id] = {}
    asset = SecurityMaster.get_asset(sedol_id, AssetIdentifier.SEDOL, sort_by_rank=True)
    identifiers_df[sedol_id]['assetId'] = asset.get_marquee_id()
    identifiers_df[sedol_id]['BCID'] = asset.get_identifiers(as_of=dt.date(2021, 6, 10))['BCID']

identifiers_df = pd.DataFrame.from_dict(identifiers_df, orient='index')

# ## Query Marquee datasets

# In[ ]:


## Get monthly ownership data    
ds = Dataset('OWNERSHIP_SCORES_MONTHLY')
data_df = ds.get_data(start=dt.date(2021, 5, 9), end=dt.date(2021, 6, 10),
                      assetId=identifiers_df.assetId.to_list())

## Get weekly flow data    
ds2 = Dataset('OWNERSHIP_SCORES_WEEKLY_FLOW')
data2_df = ds2.get_data(start=dt.date(2021, 6, 3), end=dt.date(2021, 6, 10),
                        assetId=identifiers_df.assetId.to_list())

# In[ ]:


## merge results in a summary table
ptf_df = ptf_df.merge(identifiers_df, right_index=True, left_on='SEDOL').merge(data_df, on='assetId')
ptf_df = ptf_df.merge(data2_df, on='assetId')

# ## Explore the data

# In[ ]:


## display most passively held names
ratios_names = [x for x in ptf_df.columns if x.endswith('Ratio')]
ptf_df[['BCID']+ratios_names].sort_values(by='passiveRatio', ascending=False).head()

# In[ ]:


## display least passively held names
ptf_df[['BCID']+ratios_names].sort_values(by='passiveRatio', ascending=True).head()

# In[ ]:


## display most affected by passive inflows
ptf_df[['BCID']+ratios_names].sort_values(by='passiveFlowRatio', ascending=False).head()

# In[ ]:


## display most affected by passive outflows
ptf_df[['BCID']+ratios_names].sort_values(by='passiveFlowRatio', ascending=True).head()

# ## Compute impact of trade on portfolio-level ownership 

# In[ ]:


# plot breakdown by passive ETF ratio
own_slices = [(-3, -2), (-2, -1), (-1, 0), (0, 1), (1, 2), (2, 3.1)]
slice_labels = ['[-3,-2)', '[-2,-1)', '[-1,0)', '[0,1)', '[1,2)', '[2,3]']
# scores are bounded between -3 and 3

# compute total value sold and bought
tot_traded_long = ptf_df.loc[ptf_df['Value']>0].sum()['Value']
tot_traded_short = ptf_df.loc[ptf_df['Value']<0].sum()['Value']

# compute values traded and plot bars
text_kwargs = dict(ha='center', va='center', fontsize=12, color='black')
fig, ax = plt.subplots(2, 1, figsize=(8, 12))
cnc = 0
for etf_var, var_label, chart_title in [('passiveEtfRatio', 'Passive ETF ratio', 'Breakdown by ETF ownership'),
                                        ('etfFlowRatio', 'Passive ETF flow ratio', 'Breakdown by ETF flows')]:
    slc = 0
    for lb, ub in own_slices:
        ax[cnc].barh(slc, ptf_df.loc[(ptf_df[etf_var]>=lb) & (ptf_df[etf_var]<ub) 
            & (ptf_df['Value']>0)].sum()['Value']/tot_traded_long, color='#939393')
        ax[cnc].barh(slc, -ptf_df.loc[(ptf_df[etf_var]>=lb) & (ptf_df[etf_var]<ub) 
            & (ptf_df['Value']<0)].sum()['Value']/tot_traded_short, color='#7399c6')
        slc += 1
    ax[cnc].set_xlabel('Proportion of value traded')
    ax[cnc].set_ylabel(var_label)
    ax[cnc].set_yticks(range(6))
    ax[cnc].set_yticklabels(slice_labels)
    ax[cnc].set_title(chart_title)
    cnc += 1
plt.text(0.6, 5, 'Buys', **text_kwargs)
plt.text(-0.25, 5, 'Sells', **text_kwargs)
plt.text(0.6, 12.75, 'Buys', **text_kwargs)
plt.text(-0.25, 12.75, 'Sells', **text_kwargs)
plt.show()

# In[ ]:


# compute portfolio-level change
ptf_delta = {}
for si in ['passiveRatio', 'passiveEtfRatio']:
    ptf_delta[si] = sum(ptf_df[si]*ptf_df['Value'])/1.0e+09 
ptf_delta

# ##### Disclaimers:
# ###### Indicative Terms/Pricing Levels: This material may contain indicative terms only, including but not limited to pricing levels. There is no representation that any transaction can or could have been effected at such terms or prices. Proposed terms and conditions are for discussion purposes only. Finalized terms and conditions are subject to further discussion and negotiation.
# ###### www.goldmansachs.com/disclaimer/sales-and-trading-invest-rec-disclosures.html If you are not accessing this material via Marquee ContentStream, a list of the author's investment recommendations disseminated during the preceding 12 months and the proportion of the author's recommendations that are 'buy', 'hold', 'sell' or other over the previous 12 months is available by logging into Marquee ContentStream using the link below. Alternatively, if you do not have access to Marquee ContentStream, please contact your usual GS representative who will be able to provide this information to you.
# ###### Please refer to https://marquee.gs.com/studio/ for price information of corporate equity securities.
# ###### Notice to Australian Investors: When this document is disseminated in Australia by Goldman Sachs & Co. LLC ("GSCO"), Goldman Sachs International ("GSI"), Goldman Sachs Bank Europe SE ("GSBE"), Goldman Sachs (Asia) L.L.C. ("GSALLC"), or Goldman Sachs (Singapore) Pte ("GSSP") (collectively the "GS entities"), this document, and any access to it, is intended only for a person that has first satisfied the GS entities that: 
# ###### • the person is a Sophisticated or Professional Investor for the purposes of section 708 of the Corporations Act of Australia; and 
# ###### • the person is a wholesale client for the purpose of section 761G of the Corporations Act of Australia. 
# ###### To the extent that the GS entities are providing a financial service in Australia, the GS entities are each exempt from the requirement to hold an Australian financial services licence for the financial services they provide in Australia. Each of the GS entities are regulated by a foreign regulator under foreign laws which differ from Australian laws, specifically: 
# ###### • GSCO is regulated by the US Securities and Exchange Commission under US laws;
# ###### • GSI is authorised by the Prudential Regulation Authority and regulated by the Financial Conduct Authority and the Prudential Regulation Authority, under UK laws;
# ###### • GSBE is subject to direct prudential supervision by the European Central Bank and in other respects is supervised by the German Federal Financial Supervisory Authority (Bundesanstalt für Finanzdienstleistungsaufischt, BaFin) and Deutsche Bundesbank;
# ###### • GSALLC is regulated by the Hong Kong Securities and Futures Commission under Hong Kong laws; and
# ###### • GSSP is regulated by the Monetary Authority of Singapore under Singapore laws.
# ###### Notice to Brazilian Investors
# ###### Marquee is not meant for the general public in Brazil. The services or products provided by or through Marquee, at any time, may not be offered or sold to the general public in Brazil. You have received a password granting access to Marquee exclusively due to your existing relationship with a GS business located in Brazil. The selection and engagement with any of the offered services or products through Marquee, at any time, will be carried out directly by you. Before acting to implement any chosen service or products, provided by or through Marquee you should consider, at your sole discretion, whether it is suitable for your particular circumstances and, if necessary, seek professional advice. Any steps necessary in order to implement the chosen service or product, including but not limited to remittance of funds, shall be carried out at your discretion. Accordingly, such services and products have not been and will not be publicly issued, placed, distributed, offered or negotiated in the Brazilian capital markets and, as a result, they have not been and will not be registered with the Brazilian Securities and Exchange Commission (Comissão de Valores Mobiliários), nor have they been submitted to the foregoing agency for approval. Documents relating to such services or products, as well as the information contained therein, may not be supplied to the general public in Brazil, as the offering of such services or products is not a public offering in Brazil, nor used in connection with any offer for subscription or sale of securities to the general public in Brazil.
# ###### The offer of any securities mentioned in this message may not be made to the general public in Brazil. Accordingly, any such securities have not been nor will they be registered with the Brazilian Securities and Exchange Commission (Comissão de Valores Mobiliários) nor has any offer been submitted to the foregoing agency for approval. Documents relating to the offer, as well as the information contained therein, may not be supplied to the public in Brazil, as the offer is not a public offering of securities in Brazil. These terms will apply on every access to Marquee.
# ###### Ouvidoria Goldman Sachs Brasil: 0800 727 5764 e/ou ouvidoriagoldmansachs@gs.com
# ###### Horário de funcionamento: segunda-feira à sexta-feira (exceto feriados), das 9hs às 18hs.
# ###### Ombudsman Goldman Sachs Brazil: 0800 727 5764 and / or ouvidoriagoldmansachs@gs.com
# ###### Available Weekdays (except holidays), from 9 am to 6 pm.
#  
# ###### Note to Investors in Israel: GS is not licensed to provide investment advice or investment management services under Israeli law.
# ###### Notice to Investors in Japan
# ###### Marquee is made available in Japan by Goldman Sachs Japan Co., Ltd.
# 
# ###### 本書は情報の提供を目的としております。また、売却・購入が違法となるような法域での有価証券その他の売却若しくは購入を勧めるものでもありません。ゴールドマン・サックスは本書内の取引又はストラクチャーの勧誘を行うものではございません。これらの取引又はストラクチャーは、社内及び法規制等の承認等次第で実際にはご提供できない場合がございます。
# 
# ###### <適格機関投資家限定　転売制限>
# ###### ゴールドマン・サックス証券株式会社が適格機関投資家のみを相手方として取得申込みの勧誘（取得勧誘）又は売付けの申込み若しくは買付けの申込みの勧誘(売付け勧誘等)を行う本有価証券には、適格機関投資家に譲渡する場合以外の譲渡が禁止される旨の制限が付されています。本有価証券は金融商品取引法第４条に基づく財務局に対する届出が行われておりません。なお、本告知はお客様によるご同意のもとに、電磁的に交付させていただいております。
# ###### ＜適格機関投資家用資料＞ 
# ###### 本資料は、適格機関投資家のお客さまのみを対象に作成されたものです。本資料における金融商品は適格機関投資家のお客さまのみがお取引可能であり、適格機関投資家以外のお客さまからのご注文等はお受けできませんので、ご注意ください。 商号等/ゴールドマン・サックス証券株式会社 金融商品取引業者　関東財務局長（金商）第６９号 
# ###### 加入協会/　日本証券業協会、一般社団法人金融先物取引業協会、一般社団法人第二種金融商品取引業協会 
# ###### 本書又はその添付資料に信用格付が記載されている場合、日本格付研究所（JCR）及び格付投資情報センター（R&I）による格付は、登録信用格付業者による格付（登録格付）です。その他の格付は登録格付である旨の記載がない場合は、無登録格付です。無登録格付を投資判断に利用する前に、「無登録格付に関する説明書」（http://www.goldmansachs.com/disclaimer/ratings.html）を十分にお読みください。 
# ###### If any credit ratings are contained in this material or any attachments, those that have been issued by Japan Credit Rating Agency, Ltd. (JCR) or Rating and Investment Information, Inc. (R&I) are credit ratings that have been issued by a credit rating agency registered in Japan (registered credit ratings). Other credit ratings are unregistered unless denoted as being registered. Before using unregistered credit ratings to make investment decisions, please carefully read "Explanation Regarding Unregistered Credit Ratings" (http://www.goldmansachs.com/disclaimer/ratings.html).
# ###### Notice to Mexican Investors: Information contained herein is not meant for the general public in Mexico. The services or products provided by or through Goldman Sachs Mexico, Casa de Bolsa, S.A. de C.V. (GS Mexico) may not be offered or sold to the general public in Mexico. You have received information herein exclusively due to your existing relationship with a GS Mexico or any other Goldman Sachs business. The selection and engagement with any of the offered services or products through GS Mexico will be carried out directly by you at your own risk. Before acting to implement any chosen service or product provided by or through GS Mexico you should consider, at your sole discretion, whether it is suitable for your particular circumstances and, if necessary, seek professional advice. Information contained herein related to GS Mexico services or products, as well as any other information, shall not be considered as a product coming from research, nor it contains any recommendation to invest, not to invest, hold or sell any security and may not be supplied to the general public in Mexico.
# ###### Notice to New Zealand Investors: When this document is disseminated in New Zealand by Goldman Sachs & Co. LLC ("GSCO") , Goldman Sachs International ("GSI"), Goldman Sachs Bank Europe SE ("GSBE"), Goldman Sachs (Asia) L.L.C. ("GSALLC") or Goldman Sachs (Singapore) Pte ("GSSP") (collectively the "GS entities"), this document, and any access to it, is intended only for a person that has first satisfied; the GS entities that the person is someone: 
# ###### (i) who is an investment business within the meaning of clause 37 of Schedule 1 of the Financial Markets Conduct Act 2013 (New Zealand) (the "FMC Act");
# ###### (ii) who meets the investment activity criteria specified in clause 38 of Schedule 1 of the FMC Act;
# ###### (iii) who is large within the meaning of clause 39 of Schedule 1 of the FMC Act; or
# ###### (iv) is a government agency within the meaning of clause 40 of Schedule 1 of the FMC Act. 
# ###### No offer to acquire the interests is being made to you in this document. Any offer will only be made in circumstances where disclosure is not required under the Financial Markets Conducts Act 2013 or the Financial Markets Conduct Regulations 2014.
# ###### Notice to Swiss Investors: This is marketing material for financial instruments or services. The information contained in this material is for general informational purposes only and does not constitute an offer, solicitation, invitation or recommendation to buy or sell any financial instruments or to provide any investment advice or service of any kind.
# ###### THE INFORMATION CONTAINED IN THIS DOCUMENT DOES NOT CONSITUTE, AND IS NOT INTENDED TO CONSTITUTE, A PUBLIC OFFER OF SECURITIES IN THE UNITED ARAB EMIRATES IN ACCORDANCE WITH THE COMMERCIAL COMPANIES LAW (FEDERAL LAW NO. 2 OF 2015), ESCA BOARD OF DIRECTORS' DECISION NO. (9/R.M.) OF 2016, ESCA CHAIRMAN DECISION NO 3/R.M. OF 2017 CONCERNING PROMOTING AND INTRODUCING REGULATIONS OR OTHERWISE UNDER THE LAWS OF THE UNITED ARAB EMIRATES. ACCORDINGLY, THE INTERESTS IN THE SECURITIES MAY NOT BE OFFERED TO THE PUBLIC IN THE UAE (INCLUDING THE DUBAI INTERNATIONAL FINANCIAL CENTRE AND THE ABU DHABI GLOBAL MARKET). THIS DOCUMENT HAS NOT BEEN APPROVED BY, OR FILED WITH THE CENTRAL BANK OF THE UNITED ARAB EMIRATES, THE SECURITIES AND COMMODITIES AUTHORITY, THE DUBAI FINANCIAL SERVICES AUTHORITY, THE FINANCIAL SERVICES REGULATORY AUTHORITY OR ANY OTHER RELEVANT LICENSING AUTHORITIES IN THE UNITED ARAB EMIRATES. IF YOU DO NOT UNDERSTAND THE CONTENTS OF THIS DOCUMENT, YOU SHOULD CONSULT WITH A FINANCIAL ADVISOR. THIS DOCUMENT IS PROVIDED TO THE RECIPIENT ONLY AND SHOULD NOT BE PROVIDED TO OR RELIED ON BY ANY OTHER PERSON.

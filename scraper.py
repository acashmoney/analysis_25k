# Import required libraries
from bs4 import BeautifulSoup
from tqdm import tqdm_notebook
import requests
import re
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

def pull_results(soup):
    clean = []
    pull = soup.find_all('span', attrs={'class': re.compile("icon-font-chess square")})

    for i in pull:
        if 'minus' in str(i):
            clean.append('loss')
        elif 'plus' in str(i):
            clean.append('win')
        elif 'equal' in str(i):
            clean.append('draw')
        else:
            clean.append('error')

    return clean

def pull_moves(soup):
    moves = []
    for i in soup.find_all('td', attrs={'class': re.compile("table-text-center")}):
        if i.find('span'):
            moves.append(int(i.find('span').text))
            
    return moves

def pull_dates(soup):
    dates = []
    for i in soup.find_all('td', attrs={'class': re.compile('table-text-right archive-games-date-cell')}):
        dates.append(i.getText().strip())

    return dates

def pull_speed(soup):
    times = []
    for i in soup.find_all('span', attrs={'class': re.compile('archive-games-game-time')}):
        times.append((i.getText().strip()))

    return times

def remove_dups(duplicate):
    final_list = []
    for num in duplicate:
        if num not in final_list:
            final_list.append(num)
    
    return final_list

def pull_game_links(soup):
    links = []
    for i in soup.find_all('td', attrs={'class': re.compile('table-text-center archive-games-analyze-cell')}):
        for j in i.find_all('a'):
            links.append(j.get('href'))

    return remove_dups(links)

def find_color(text):
    if 'white' in str(text):
        return 'white'
    elif 'black' in str(text):
        return 'black'
    else:
        return 'error'

def check_handle(text):
    if text == 'e4ofHearts':
        return True
    else:
        return False

def pull_player_stats(soup):
    my_rating_1st = []
    opponent_rating_1st = []
    opponent_country_1st = []
    opponent_name_1st = []
    my_color_1st = []

    for cell in soup.find_all('td', {'class': 'archive-games-user-cell'}):
        top_half = cell.find_all('div', {'class': 'post-view-meta-user'})[0]
        bottom_half = cell.find_all('div', {'class': 'post-view-meta-user'})[1]

        top_name = top_half.find('a', {'class': 'post-view-meta-username v-user-popover'}).text.strip()
        bottom_name = bottom_half.find('a', {'class': 'post-view-meta-username v-user-popover'}).text.strip()

        if check_handle(top_name) is True:
            my_rating = top_half.find('span', {'class': 'post-view-meta-rating'}).text
            my_color = 'white'
            opponent_rating = bottom_half.find('span', {'class': 'post-view-meta-rating'}).text
            opponent_country = bottom_half.find('div').get('v-tooltip')
            opponent_name = bottom_name
        else:
            my_rating = bottom_half.find('span', {'class': 'post-view-meta-rating'}).text
            my_color = 'black'
            opponent_rating = top_half.find('span', {'class': 'post-view-meta-rating'}).text
            opponent_country = top_half.find('div').get('v-tooltip')
            opponent_name = top_name
        
        my_rating = int(my_rating.replace('(','').replace(')',''))
        opponent_rating = int(opponent_rating.replace('(','').replace(')',''))
        opponent_country = opponent_country.replace("'","")

        my_rating_1st.append(my_rating)
        my_color_1st.append(my_color)
        opponent_rating_1st.append(opponent_rating)
        opponent_country_1st.append(opponent_country)
        opponent_name_1st.append(opponent_name)
    
    return(my_rating_1st, opponent_rating_1st, opponent_country_1st, opponent_name_1st, my_color_1st)

# Initialize data
results = []
moves = []
dates = []
speed = []
games = []
my_rating = []
my_color = []
opponent_rating = []
opponent_color = []
opponent_country = []
opponent_name = []

print("Initializing scrape...")

# Pull data from archived pages
for i in range(1,6):
    url_base = 'https://www.chess.com/games/archive/e4ofhearts?gameOwner=other_game&gameType=live&endDate%5Bdate%5D=03/12/2020&startDate%5Bdate%5D=02/28/2020&timeSort=desc&gameTypes%5B0%5D=chess960&gameTypes%5B1%5D=daily&page='
    paged_url = url_base + str(i)
    html = requests.get(paged_url)
    with open('./page{}.html'.format(i), 'w') as file:
        file.write(html.text)

    b = BeautifulSoup(html.text, 'html.parser')

    results += pull_results(b)
    moves += pull_moves(b)
    dates += pull_dates(b)
    speed += pull_speed(b)
    games += pull_game_links(b)
    my_rating += pull_player_stats(b)[0]
    opponent_rating += pull_player_stats(b)[1]
    opponent_country += pull_player_stats(b)[2]
    opponent_name += pull_player_stats(b)[3]
    my_color += pull_player_stats(b)[4]

    print('Page #: ' + str(i))

d = {'Date': dates,
    'Result': results,
    'Move_Count': moves,
    'Time_Control': speed,
    'Game_Link': games,
    'My_Rating': my_rating,
    'Opponent_Rating': opponent_rating,
    'Opponent_Country': opponent_country,
    'Opponent_Name': opponent_name,
    'Color_Played': my_color}

games_df = pd.DataFrame(d)

# Get rid of bullet, start from 2400 and reverse index
games_df = games_df.iloc[::-1].reset_index()
games_df = games_df[games_df.Time_Control != '1 min']
games_df = games_df[4:]
games_df.index = np.arange(1, len(games_df)+1)

# Convert dates to datetime and calculate 7-day moving average
games_df['Date'] = pd.to_datetime(games_df['Date'])
games_df['My_Rating_Moving_Average'] = games_df['My_Rating'][::-1].rolling(window=7).mean()

# Calculate win, loss and draw counts and average opponent rating for each condition
game_count = games_df['Result'].count()
results_count = games_df.groupby('Result').count()
results_mean = games_df.groupby('Result').mean()
opp_rating_avg_win = results_mean.loc['win', 'Opponent_Rating']
opp_rating_avg_loss = results_mean.loc['loss', 'Opponent_Rating']
opp_rating_avg_draw = results_mean.loc['draw', 'Opponent_Rating']
opp_ratings = [opp_rating_avg_win, opp_rating_avg_loss, opp_rating_avg_draw]

# Calculate percentages for each type of result
win_count = results_count.loc['win', 'index']
win_pct = win_count / game_count
loss_count = results_count.loc['loss', 'index']
loss_pct = loss_count / game_count
draw_count = results_count.loc['draw', 'index']
draw_pct = draw_count / game_count

# Create results dataframe for easy access to values
results_data = {'Result': ['Win','Loss','Draw'], 'Count':[win_count,loss_count,draw_count], 'Percentage':[win_pct,loss_pct,draw_pct], 'Opp_Ratings':opp_ratings}
results_df = pd.DataFrame(results_data)
print(results_df)

games_df.to_csv(path_or_buf='./Road_to_2500_games.csv')

# # Create rating progression graph
# sns.set_style('white')
# plt.figure(figsize=(13,7))
# sns.lineplot(y='My_Rating', x=games_df.index, data=games_df, color='darkslategray')
# sns.lineplot(y='My_Rating_Moving_Average', x=games_df.index, data=games_df, color='red')
# plt.xlabel('Number of Games', fontsize=13)
# plt.ylabel('My Rating', fontsize=13)
# plt.title('The Road to 2500', fontsize=13)
# plt.xlim(0)
# plt.legend(['Rating', '7-day MA'])
# plt.savefig('rating_graph.png')

# Create pie plot for results
fig, ax = plt.subplots(figsize=(12,12))
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['text.color'] = 'black'
plt.rcParams['axes.labelcolor'] = 'black'
plt.rcParams['xtick.color'] = 'black'
plt.rcParams['ytick.color'] = 'black'
plt.rcParams['font.size'] = 12

# Create custom labels
labels = []
for i in range(0,3):
    labels.append(str(results_df.loc[i]['Result']) + '\n(Opponent Avg: ' + str(round(int(results_df.loc[i]['Opp_Ratings']))) + ')')

counts = results_data['Count']
ratings = results_data['Opp_Ratings']

def make_autopct(values):
    def my_autopct(pct):
        total = game_count
        val = int(round(pct*total/100.0))
        return str('{p:.1f}% ({v:d})'.format(p=pct, v=val))
    return my_autopct

ax.pie(counts, labels=labels, autopct=make_autopct(counts), colors={'forestgreen','lightcoral','cornflowerblue'})
ax.set_title('Road to 2500 Results')

plt.savefig('results_plot.png')
plt.show()
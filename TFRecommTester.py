from pandas import DataFrame
from io import StringIO
from functools import reduce
import pandas as pd
import os
import io
import sys
import telnetlib
import time
import numpy
import itertools

#read movies data (users.dat must be in the local directory)
movies = pd.read_table('movies.dat', sep='::', comment='#', header=None)
movies = movies.rename(columns={0:'ID'})
movies = movies.rename(columns={1:'FilmTitle'})
movies = movies.rename(columns={2:'Genre'})
movies = movies.rename(columns={3:'Rating'})

#function to get recommendations
def getRecomm(subset):
        tn_read_apend = ""

        #create a list that will store the results from the recommender API
        df_list = []

        #create a list that will store all the ratings that came back for a given subset of users with the same demographic (and age)
        ratings_list = []

        #create a list that will store all the genres found for that user's set of recommendations
        genres_list = []


        #iterate over the subset of users who have similar demographic and invoke the TF-Recomm model to get their recommendation
        for index, row in subset.iterrows():
                string = ""+str(row[0])+""
                tn.write((string + "\r\n").encode('ascii'))
                time.sleep(1)
                tn_read =  tn.read_very_eager()
                tn_read_apend =  tn_read_apend + str(tn_read)

                #wrangle the response to manipulate spurious characters
                tn_read_cleaned = str(tn_read_apend).replace("b\"", "")
                tn_read_cleaned = str(tn_read_cleaned).replace("\"", "")
                tn_read_cleaned = str(tn_read_cleaned).replace("):", ")^")
                tn_read_cleaned = str(tn_read_cleaned).replace("\^", "::")
                tn_read_cleaned = str(tn_read_cleaned).replace("^", "::")

                #add columns for Film and Genre
                tn_read_cleaned = "Film::Genre\n"+tn_read_cleaned
                mytext = "\r\n".join(str(tn_read_cleaned).split('\\n'))
                TESTDATA=StringIO(mytext)

                #read into a dataframe and append to a list
                df = pd.read_csv(TESTDATA, sep="::")
                
                #set user age
                df['UserAge'] = row[2]

                #this nested loop is to get the ratings for each film recommendation
                movieRatingList = []
                count =0
                #iterate over the recommendations for the user
                for index, row in df.iterrows():
                    userFilm = row['Film']
                    genres_list.append(row['Genre'])
                    movieRating = ""
                    #as normal indexing wiith dymanic values does not work, need to loop over each movie in the movies dataset
                    #taking advantage of lexical scoping to reverence "movies" variable that has not been declared within the function!
                    for index, movie in movies.iterrows():
                        movieFile = str(movie['FilmTitle'])
                        #match on the movie in the full data set that matches the user movie in the current iteration of loop                      
                        if str(movieFile) == str(userFilm):
                            #get the rating
                            movieRating = str(movie['Rating'])
                            #append to the long list of ratings for this user
                            ratings_list.append(movieRating)
                            #break out of the loop when year matches
                            break
                    movieRatingList.append(movieRating)
                #add the ratings as a column to the user recommendations dataframe
                df['MovieRating'] =  movieRatingList                   
                
                
                #print the dataframe for the user's recommendation
                #print(df)
                df_list.append(df)
                tn_read_apend = ""

        index = numpy.arange(len(ratings_list)) 
        columns = ['Ratings']
        ratings_list_df = pd.DataFrame(index=index, columns=columns)
        ratings_list_df['Ratings'] = ratings_list               

        #set up a vector that is going to be the return value of the function (will return the number of matches from each user pair compared)
        pair_vector = []
        iterate = 'true'
        iterator = 1
        end = len(df_list)
        index1 = 0

        # recursive algorithm that ensures that all possible unique combinations of row pairs in the subset 
        # are actually compared (e.g. for 3 rows; row 0 and row 1, row 0 and row 2, row 1 & row 2)
        while iterate != 'false':
            countInterator = iterator+1
            countindex1 = index1+1           
            if (index1 >= iterator):
                    iterator += 1
                    continue
            if (iterator==len(df_list) and countindex1!=len(df_list)):
                    iterator = 1
                    index1 +=1
                    continue
            if (countindex1==len(df_list)):
                    iterate = 'false'
                    break            
            #print("comparing "+str(index1)+" and "+str(iterator)+"on this iteration")

            #find distinct 1-2-1 matches between row pairs based on genre
            #this is to give a feel for similarity between user recommendations
            pair = pd.merge(df_list[index1], df_list[iterator], on=['Genre'], how='inner')

            # remove "double counting"  caused by merge function
            pair = pair.drop_duplicates(subset=['Film_x'])
            pair = pair.drop_duplicates(subset=['Film_y'])

            #append the number of matches in this pair to a vector
            pair_vector.append(len(pair))
            iterator += 1

        noOfMatches = sum(pair_vector)

        #output the totals and generate summary statistics for film ratings.
        total_genres = len(set(genres_list))
        genre_percent = noOfMatches / total_genres
        print("Found "+str(round(noOfMatches,3))+ " genre matches between user pairs, out of "+str(total_genres)+" genres across the recommendations for this subset of "+str(len(subset))+" user recommendations")
        print("Users age is "+str(subset[2].iloc[0])+". Summary statistics for film certification/ratings for this pair/subset were:")
        ratings_list_series = ratings_list_df['Ratings'].value_counts()
        summary_stats = pd.DataFrame({ 'Frequency':ratings_list_series.values ,'Rating':ratings_list_series.index})
        percentages = []
        for index, row in summary_stats.iterrows():
                percentage = row['Frequency']/len(ratings_list_df)
                percentages.append(percentage)
        summary_stats['Percentage'] = percentages
        print(summary_stats)
        #return the vector of pairs containing the match numbers for each pair              
        return pair_vector

        
#get telnet session to the container
tn = telnetlib.Telnet("192.168.99.100", 81)

#read user data (users.dat must be in the local directory)
usersDF = pd.read_table('users.dat', sep='::', comment='#', header=None)

#group by the rows users.dat where all 4 column values are the same
permutations = usersDF.groupby([1,2,3,4]).size().reset_index().rename(columns={0:'count'})

#subset the permutations data frame to ones where count is greater than 1
#NOTE: the below value produces about 195 pairs and takes a log time to cycle! for a smaller subset, change this to > 5
subsetPerms = permutations[(permutations['count'] > 5)]
              

print("executing permutations of users from same demographic....") 

#create a list that will store the genre matches for each pair of users, in order to roll them up at the end
genre_match_averages = []
for index, row in subsetPerms.iterrows():
        subset = usersDF[(usersDF[1] == row[1])&(usersDF[2] == row[2])&(usersDF[3] == row[3])&(usersDF[4] == row[4])]
        #print(subset)
        genreMatch = getRecomm(subset)
        genre_match_averages.append(genreMatch)

#flatten out the vector of vectors to leave all the numbers of matches for each pair that was compared.         
merged = list(itertools.chain(*genre_match_averages))
        
print("The average number of distinct genre matches for users in a correlated demographic was "+str(round(sum(merged)/len(merged),2)))   


#print("executing random permutations....")        

#create a list that will store the genre matches from random samples to compare with correlated groups
genre_match_averages_random = []

for index, row in subsetPerms.iterrows():
        subset = usersDF.sample(frac=0.1)
        subset = subset.head(5)
        genreMatch = getRecomm(subset)
        genre_match_averages_random.append(genreMatch)

merged = list(itertools.chain(*genre_match_averages_random))       
print("The average number of distinct genre matches between different users across a random sample was "+str(round(sum(merged)/len(merged),2)))

#compare movie ratings with user's age... (this will run slowly!!)

#explicitly select age column and subset by age of "1"      

subset = usersDF[(usersDF[2] == 1)].sample(frac=0.50)

#get the first 50
subset = subset.head(100)

getRecomm(subset)

#explicitly select age column and subset by age of greater than "18"
subset = usersDF[(usersDF[2] >= 18)].sample(frac=0.50)

#get the first 50
subset = subset.head(100)

getRecomm(subset)

#compare males & females
genre_match_averages_random = []

for index, row in subsetPerms.iterrows():
        subset = usersDF[(usersDF[1] == 'F')].sample(frac=0.1)
        subset = subset.head(5)
        genreMatch = getRecomm(subset)
        genre_match_averages_random.append(genreMatch)

merged = list(itertools.chain(*genre_match_averages_random)) 
print("The average number of distinct genre matches for females was "+str(round(sum(merged)/len(merged),2)))        

genre_match_averages_random = []

for index, row in subsetPerms.iterrows():
        subset = usersDF[(usersDF[1] == 'M')].sample(frac=0.1)
        subset = subset.head(2)
        genreMatch = getRecomm(subset)
        genre_match_averages_random.append(genreMatch)

merged = list(itertools.chain(*genre_match_averages_random)) 
print("The average number of distinct genre matches for males was "+str(round(sum(merged)/len(merged),2)))   



        

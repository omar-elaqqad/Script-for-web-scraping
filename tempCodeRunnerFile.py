
        if len(group) > 0:
            # Filter out scores with Odds< 1%
            filtered_scores = group[group['Odds(%)'] >= 1]
            # Sort scores in descending order
            sorted_scores = filtered_scores.sort_values(by='Odds(%)', ascending=False)
            
            # Safely access the first elements for printing
            home_country = group.iloc[0]['Home Country']
            away_country = group.iloc[0]['Away Country']
            print(f"Match: {home_country} vs {away_country}")
            score_odds = sorted_scores[['Score', 'Odds(%)']]
            probability_by_score = score_odds[score_odds['Odds(%)']>=5].to_dict('records')
            score_odds['Expected Points'] = score_odds.apply(lambda row: calculate_expected_points(row['Score'], probability_by_score), axis=1)

            print(score_odds[score_odds['Odds(%)']>=5])
            print("\n")  # Add a newline for better readability between matches



pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
fixtures_df = scrape_euro_fixtures()
if fixtures_df is not None:
    print(fixtures_df)
    odds_df = scrape_odds_data(fixtures_df)

    if odds_df is not None:
        take_average(odds_df)

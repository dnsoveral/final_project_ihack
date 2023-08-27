import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from textwrap import wrap
from urllib.parse import quote
from io import BytesIO
from reportlab.lib.utils import open_for_read
import requests
import random
from IPython.display import clear_output


def create_mapping(data, columns):
    """
    Create a mapping dictionary by calculating the average cosine similarity for each category in the specified columns.

    Args:
        data (pd.DataFrame): DataFrame containing the cosine similarity data.
        columns (list): List of columns to create mappings for.

    Returns:
        dict: A dictionary mapping category names to their average cosine similarity values.
    """
    mapping = {}

    for column in columns:
        unique_categories = data[column].unique()
        avg_cosine_scores = {}

        for category in unique_categories:
            avg_cosine_scores[category] = data[data[column] == category]['avg_cosine'].mean()

        mapping[column] = avg_cosine_scores

    return mapping

def generate_meal_plan_with_user_preferences(num_days, df):
    """
    Generate a meal plan based on user preferences.

    Args:
        num_days (int): Number of days for the meal plan.
        df (DataFrame): DataFrame containing meal data with columns 'meal_class' and 'time(min)'.

    Returns:
        dict: A nested dictionary representing meal plans for each day.
    """
    meal_plan = {}

    for day in range(1, num_days + 1):
        print(f"Preferences for Day {day}:")
        day_preferences = {}

        # Ask the user for cost and difficulty preferences for the day
        day_preferences['Preference for Cost'] = input(f"Enter your Cost Preference for Day {day} (Económico, Médio, Dispendioso) for the Chef to consider: ")
        day_preferences['Preference for Difficulty'] = input(f"Enter your Difficulty Preference for Day {day} (Fácil, Médio, Difícil) for the Chef to consider: ")

        # Ask the user for meal class preferences as a comma-separated string
        meal_class_preferences = input(f"Enter Meal Class Preferences for Day {day} (comma-separated, choose from: Doces e Sobremesas, Carnes, Sopas, Peixes) for the Chef to consider: ")

        # Split the input string into a list of meal classes
        meal_class_preferences_list = [preference.strip() for preference in meal_class_preferences.split(',')]

        # Initialize a dictionary to store preferences for each meal class
        meal_preferences = {}

        # For each meal class, find the minimum and maximum times
        for meal_class in meal_class_preferences_list:
            min_time = df[df['meal_class'] == meal_class]['time(min)'].min()
            max_time = df[df['meal_class'] == meal_class]['time(min)'].max()
            
            while True:
                try:
                    time_preference = int(input(f"Enter your Time Preference for {meal_class} on Day {day} (in minutes, between {min_time} and {max_time}, in intervals of 15): "))
                    if time_preference < min_time or time_preference > max_time or (time_preference - min_time) % 15 != 0:
                        raise ValueError(f"Time preference must be between {min_time} and {max_time} minutes and in intervals of 15 minutes.")
                    break
                except ValueError as e:
                    print(e)

            # Store the time preference in the meal_preferences dictionary
            meal_preferences[meal_class] = f"{time_preference}"

        # Add the meal_preferences dictionary to day_preferences
        day_preferences['Meal Preferences'] = meal_preferences

        # Append the day's preferences to the meal_plan dictionary
        meal_plan[f"Day {day}"] = day_preferences

        # Print all preferences for the day
        print(f"These are your Preferences for the Meal Plan for Day {day}:")
        for key, value in day_preferences.items():
            if key == 'Meal Preferences':
                print("Meal Preferences:")
                for meal_class, time_preference in value.items():
                    print(f"{meal_class}: {time_preference}")
            else:
                print(f"{key}: {value}")

    return meal_plan

 # Load the dataset
df = pd.read_csv('../data/clean/recipes.csv')

columns_to_map = ['cost', 'difficulty', 'meal_class']
mappings = create_mapping(df, columns_to_map)

cost_mapping = mappings['cost']
difficulty_mapping = mappings['difficulty']
meal_class_mapping = mappings['meal_class']

def map_categorical_to_cosine(meal_plan):
    """
    Map user preferences for all days in a meal plan to cosine similarity columns.

    Args:
        meal_plan (dict): User's meal plan preferences for all days.

    Returns:
        dict: Mapped preferences with cosine similarity columns for all days.
    """
    mapped_preferences = {}
    
    for day, preferences in meal_plan.items():
        mapped_day_preferences = {
            'cost_cosine': cost_mapping[preferences['Preference for Cost']],
            'difficulty_cosine': difficulty_mapping[preferences['Preference for Difficulty']],
        }

        # Initialize a dictionary to store meal class cosine values
        meal_class_cosines = {}

        # Iterate through the meal preferences for the day
        if 'Meal Preferences' in preferences:
            for meal_class, time in preferences['Meal Preferences'].items():
                # Calculate and store the cosine similarity for each meal class
                meal_class_cosines[meal_class] = {
                    'cosine_similarity': meal_class_mapping[meal_class],
                    'time': time
                }

        # Add the meal class cosine similarity values to the mapped preferences
        mapped_day_preferences['meal_class_cosines'] = meal_class_cosines

        # Add the mapped preferences for the day to the overall mapped_preferences
        mapped_preferences[day] = mapped_day_preferences
    
    return mapped_preferences

def calculate_avg_cosine_similarity(data):
    """
    Calculate the average cosine similarity for each meal class by day based on the provided data.

    Parameters:
    data (dict): A dictionary containing cosine similarity data for each recipe.

    Returns:
    dict: A dictionary where keys are day and meal class combinations, and values are the average cosine similarity.
    """
    avg_cosine_similarity = {}

    for day, day_data in data.items():
        meal_class_cosines = day_data.get('meal_class_cosines', {})

        for meal_class, cosine_data in meal_class_cosines.items():
            key = f"{day}: {meal_class}"
            if key not in avg_cosine_similarity:
                avg_cosine_similarity[key] = {'cosine_similarity': [], 'time': []}

            avg_cosine_similarity[key]['cosine_similarity'].append(cosine_data['cosine_similarity'])
            avg_cosine_similarity[key]['time'].append(cosine_data['time'])

    return avg_cosine_similarity

def find_highest_similarity_recipes(df, avg_cosine_similarity):
    """
    Find the most similar recipe in the base dataset for each day and meal class,
    based on the provided user meal preferences, while considering a maximum time constraint
    per meal.

    Parameters:
    df (pd.DataFrame): The DataFrame containing recipe data, including 'avg_cosine' and 'time' columns.
    avg_cosine_similarity (dict): The user's meal preferences with cosine values for each day, meal class combination.

    Returns:
    dict: A dictionary where keys are day and meal class combinations, and values are dictionaries
          containing the title and img_url of the most similar recipe that meets the specified criteria.
    """
    
    highest_similarity_recipes = {}

    # Iterate through the avg_cosine_similarity dictionary
    for day_meal_class, preferences in avg_cosine_similarity.items():
        
        # Split the day_meal_class correctly
        
        parts = day_meal_class.split(": ")
        
        if len(parts) != 2:
            
            continue  # Skip this entry if it doesn't have the expected format
            
        day, meal_class = parts

        cosine_similarity = preferences['cosine_similarity'][0]  # Get the first element from the list

        if cosine_similarity > -0.65: 
            max_time_minutes = int(preferences['time'][0])  

            # Filter recipes by meal class and within the maximum time constraint
            similar_recipes = df[(df['meal_class'] == meal_class) & (df['avg_cosine'] > 0) & (df['time(min)'] <= max_time_minutes)]

            if not similar_recipes.empty:
                # Sort the similar recipes by cosine similarity in descending order
                similar_recipes = similar_recipes.sort_values(by='avg_cosine', ascending=False)

                # Extract the meal class name with the day prefix
                meal_class_name = f"{day_meal_class}"

                if meal_class_name not in highest_similarity_recipes:
                    highest_similarity_recipes[meal_class_name] = {}

                # Retrieve the topmost similar recipe for each day and meal class
                top_recipe = similar_recipes.iloc[0]
                recipe_title = top_recipe['title']
                img_url = top_recipe['image_url']

                highest_similarity_recipes[meal_class_name] = {'title': recipe_title, 'image_url': img_url}

    return highest_similarity_recipes

def save_meal_plan_to_pdf(highest_similarity_recipes, df, num_days):
    """
    Save a meal plan to a PDF file.

    Args:
        highest_similarity_recipes (dict): Dictionary containing meal plan data.
        df (DataFrame): The DataFrame containing recipe information.
        num_days (int): Number of days in the meal plan.
    """
    pdf_filename = f"meal_plan_for_{num_days}_days.pdf"
    
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
    
    styles = getSampleStyleSheet()

    # Create a list to store story elements
    story = []

    # Define a custom style for the title
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading2'],
        fontSize=16,
        fontName='Helvetica-Bold',
        alignment=0,
        spaceAfter=6
    )

    # Define a custom style for other text elements
    text_style = ParagraphStyle(
        name='TextStyle',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica',
        alignment=0,
        spaceAfter=12
    )
    
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])

    # Iterate through each recipe for the day
    for day_key, recipe_data in highest_similarity_recipes.items():
        parts = day_key.split(': ')

        if len(parts) == 2:
            day = parts[0]  
            m_class = parts[1]  
            title = recipe_data['title'] 
        
            # Check if the title exists in the DataFrame
            if title in df['title'].tolist():
                    
                # Find the recipe information in the DataFrame based on the title
                recipe_info = df[df['title'] == title].iloc[0]
                
                meal_class = recipe_info['meal_class']
                servings = recipe_info['servings']
                time = recipe_info['time(min)']
                ingredients = recipe_info['ingredients_combined']
                preparations = recipe_info['preparations']
                link = recipe_info['recipe_link']
                image = recipe_info['image_url']

                # Clean up preparations and ingredients
                preparations = ', '.join(wrap(preparations.strip("[]").replace("'", ""), width=50))
                ingredients = ', '.join(wrap(ingredients.strip("[]").replace("'", ""), width=50))

                # Create a recipe image and text section
                try:
                    response = requests.get(image)
                    response.raise_for_status()  # Raise an exception for HTTP errors
                    image_data = BytesIO(response.content)
                    image = Image(image_data, width=2.0 * inch, height=1.5 * inch)
                except Exception as e:
                    # Handle image retrieval error by displaying the image URL
                    image = Paragraph(f"Image URL: {image}", text_style)
                    
                             
                recipe_table = Table([
                    [image,
                    [Paragraph(f"{day}", title_style),
                    Paragraph(f"TITLE: {title}", title_style),
                    Paragraph(f"MEAL CLASS: {meal_class}", title_style),
                    Paragraph(f"SERVINGS: {str(servings)}", text_style),
                    Paragraph(f"TIME (min): {str(time)}", text_style),
                    Paragraph(f"INGREDIENTS: {ingredients}", text_style),
                    Paragraph(f"PREPARATIONS: {preparations}", text_style),
                    Paragraph(f"LINK: {link}", styles['Italic'])]]], colWidths=[2.0 * inch, 5.0 * inch])

                recipe_table.setStyle(TableStyle([
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))

                # Add the recipe table to the story
                story.append(recipe_table)

                # Add a page break after processing each recipe
                story.append(PageBreak())

    # Build the PDF document
    doc.build(story)

def filter_recipes(dataframe, ingredients, difficulty_filter):
    """
    Filter recipes based on user preferences.

    Args:L
        dataframe (pandas.DataFrame): The recipe dataset.
        ingredients (list): List of ingredients to filter by.
        difficulty_filter (str): Difficulty filter (e.g., 'Fácil', 'Médio').

    Returns:
        pandas.DataFrame: Filtered recipes.
    """
    filtered_df = dataframe.copy()

    for ingredient in ingredients:
        filtered_df = filtered_df[filtered_df['ingredients_combined'].str.contains(ingredient.strip())]

    filtered_df = filtered_df[(filtered_df['difficulty'] == difficulty_filter)]

    return filtered_df

def suggest_random_recipes(dataframe, num_suggestions):
    """
    Get random recipe suggestions from the filtered recipes.

    Args:
        dataframe (pandas.DataFrame): Filtered recipe dataset.
        num_suggestions (int): Number of recipe suggestions to generate.

    Returns:
        pandas.DataFrame: Randomly selected recipe suggestions.
    """
    if num_suggestions > len(dataframe):
        num_suggestions = len(dataframe)

    suggested_recipes = dataframe.sample(num_suggestions)
    return suggested_recipes

def save_single_recipe_to_pdf(suggested_recipes, recipe_data, pdf_filename):
    
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)

    # Define a custom style for the title
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading2'],
        fontSize=16,
        fontName='Helvetica-Bold',
        alignment=0,
        spaceAfter=6
    )

    # Define a custom style for other text elements
    text_style = ParagraphStyle(
        name='TextStyle',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica',
        alignment=0,
        spaceAfter=12
    )

    story = []

    # Extract recipe information from recipe_data
    title = recipe_data['title']
    meal_class = recipe_data['meal_class']
    servings = recipe_data['servings']
    time = recipe_data['time(min)']
    ingredients = recipe_data['ingredients_combined']
    preparations = recipe_data['preparations']
    link = recipe_data['recipe_link']
    recipe_image_url = recipe_data['image_url']

    # Clean up preparations and ingredients and apply text wrapping
    preparations = '\n'.join(wrap(preparations.strip("[]").replace("'", ""), width=70))
    ingredients = '\n'.join(wrap(ingredients.strip("[]").replace("'", ""), width=70))

    # Create a recipe image
    try:
        response = requests.get(recipe_image_url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        image_data = BytesIO(response.content)
        image = Image(image_data, width=2.5 * inch, height=2.0 * inch)
    except Exception as e:
        # Handle image retrieval error by providing a default image or message
        image = print(f"{image_url}")

    recipe_table = Table([
        [image,
        [Paragraph(f"TITLE: {title}", title_style),
        Paragraph(f"MEAL CLASS: {meal_class}", title_style),
        Paragraph(f"SERVINGS: {str(servings)}", text_style),
        Paragraph(f"TIME (min): {str(time)}", text_style),
        Paragraph(f"INGREDIENTS: {ingredients}", text_style),
        Paragraph(f"PREPARATIONS: {preparations}", text_style),
        Paragraph(f"LINK: {link}", styles['Italic'])]]], colWidths=[2.5 * inch, 5.0 * inch])

    recipe_table.setStyle(TableStyle([
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('VALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(recipe_table)

    # Build the PDF document
    doc.build(story)
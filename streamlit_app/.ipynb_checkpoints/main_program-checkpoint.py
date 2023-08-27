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
from functions import (create_mapping, generate_meal_plan_with_user_preferences, save_meal_plan_to_pdf, filter_recipes, suggest_random_recipes, save_single_recipe_to_pdf, map_categorical_to_cosine, calculate_avg_cosine_similarity, find_highest_similarity_recipes)
from IPython.display import clear_output


def main_program():
    # Load the dataset
    df = pd.read_csv('../data/clean/recipes.csv')

    columns_to_map = ['cost', 'difficulty', 'meal_class']
    mappings = create_mapping(df, columns_to_map)

    cost_mapping = mappings['cost']
    difficulty_mapping = mappings['difficulty']
    meal_class_mapping = mappings['meal_class']

    while True:

        print("Welcome to Chez Ratatouille!\n")

        user_has_ingredients = input("Do you have ingredients for Chef Ratatouille to help you with a Recipe? (yes/no): ").lower()

        if user_has_ingredients == "yes":

            user_ingredients = input("Enter the ingredients (comma-separated) you have available: ").split(',')
            user_difficulty_filter = input("Enter the difficulty filter (Fácil/Médio/Difícil) to help the Chef think: ")

            filtered_recipes = filter_recipes(df, user_ingredients, user_difficulty_filter)

            while True:  # Add a loop for providing more suggestions

                suggested_recipes = suggest_random_recipes(filtered_recipes, 5)

                if suggested_recipes.empty:
                    print("No recipes at Chez Ratatouille match your criteria.")
                    break  # Break out of the suggestion loop if there are no more suggestions

                print("Suggested Recipes from the Chef's Mind:")

                for idx, row in suggested_recipes.iterrows():

                    print(f"{idx + 1}. {row['title']}")
                    print(f"{idx + 1}. {row['image_url']}")

                user_choice = input("Select a recipe number for the Chef to create a PDF or type 'more' for more suggestions from the Chef, or 'no' to exit: ")

                if user_choice.isdigit():

                    recipe_idx = int(user_choice) - 1
                    recipe_data = df.iloc[recipe_idx]
                    pdf_filename = f"{recipe_data['title']}.pdf"
                    save_single_recipe_to_pdf(suggested_recipes, recipe_data, pdf_filename)
                    print("The Chef has created a PDF file for you!")
                    break

                elif user_choice.lower() == "more":
                    # Continue the loop to provide more suggestions
                    continue

                else:
                    print("Thank you for using Chez Ratatouille! Enjoy your meal!")
                    break  # Exit the suggestion loop and the main loop

            else:
                print("Thank you for using Chez Ratatouille! Enjoy your meal!")
                break  # Exit the main loop if the user doesn't have ingredients

            return_to_beginning = input("Do you want to start over at Chez Ratatouille? (yes/no): ").lower()

            if return_to_beginning == "yes":
                clear_output(wait=True)

            else:
                print("Thank you for using Chez Ratatouille! Enjoy your meal!")
                break

        elif user_has_ingredients == "no":

            clear_output(wait=True)

            print("Welcome to Chez Ratatouille Meal Planner!\n")

            user_wants_meal_plan = input("Do you want a meal plan prepared by Chef Ratatouille? (yes/no): ").lower()

            if user_wants_meal_plan == "yes":

                num_days = int(input("How many days do you want Chef Ratatouille to prepare the meal plan for? "))

                meal_plan = generate_meal_plan_with_user_preferences(num_days, df)

                map = map_categorical_to_cosine(meal_plan)

                avg_cosine_similarity = calculate_avg_cosine_similarity(map)

                highest_similarity_recipes = find_highest_similarity_recipes(df, avg_cosine_similarity)

                clear_output()

                print("The Chef suggests this Meal Plan:")
                print()

                # Iterate through the data and print the information
                for day, info in highest_similarity_recipes.items():

                    day_parts = day.split(': ')
                    day_of_recipe = day_parts[0]
                    meal_class = day_parts[1]
                    title = info.get('title')
                    image_url = info.get('image_url')

                    print(f'Day of recipe: {day_of_recipe}')
                    print(f'Meal Class: {meal_class}')
                    print(f'Title of Recipe: {title}')
                    print(f'Image URL: {image_url}\n')

                generate_pdf = input("Do you want Chef Ratatouille to print a PDF of the meal plan he prepared for you? (yes/no): ").lower()

                if generate_pdf == "yes":

                    save_meal_plan_to_pdf(highest_similarity_recipes, df, num_days)
    
                    clear_output(wait=True)

                    print("Chef Ratatouille has prepared a PDF file for you! Thank you for using Chez Ratatouille! Enjoy your meal!")

                    break

                else:

                    generate_pdf == "no"

                    print("Thank you for using Chez Ratatouille! Enjoy your meal!")

                    break

                    clear_output(wait=True)

            if not any(meal_plan):
                print("Chef Ratatouille can't think of any meal plan with your preferences. Thank you for using Chez Ratatouille!")

            else:
                print("Thank you for using Chez Ratatouille!")
            
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

if __name__ == "__main__":
    main_program()
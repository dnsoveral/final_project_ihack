import streamlit as st
import pandas as pd
from functions import (
    create_mapping,
    generate_meal_plan_with_user_preferences,
    save_meal_plan_to_pdf,
    filter_recipes,
    suggest_random_recipes,
    map_categorical_to_cosine,
    calculate_avg_cosine_similarity,
    find_highest_similarity_recipes,
    save_single_recipe_to_pdf
)

df = pd.read_csv('../data/clean/recipes.csv')
st.title("Chez Ratatouille")
col1, col2, col3 = st.columns([1, 1, 1])

# Initialize session state to manage app state
if 'user_has_ingredients' not in st.session_state:
    st.session_state.user_has_ingredients = "no"
if 'user_wants_meal_plan' not in st.session_state:
    st.session_state.user_wants_meal_plan = "no"

# Load the image
image = "ratatouille-production-stills-ratatouille-1847049-1902-2560_wgszv1.jpg"

# Display the image in the middle column
with col2:
    st.image(image, use_column_width=True)


with col1:
    st.header("Recipe Suggestions")

    user_ingredients = st.text_input("Enter the ingredients (comma-separated) you have available:")
    st.write(f"Ingredients: {user_ingredients}")
    user_difficulty_filter = st.selectbox("Enter the difficulty filter", ("Fácil", "Médio", "Difícil"))
    st.write(f"Difficulty: {user_difficulty_filter}")

    if st.button("Get Recipes"):  
        # Filter recipes based on user input
        filtered_recipes = df  # Initialize the DataFrame with all recipes
        
        if user_difficulty_filter:
            filtered_recipes = filtered_recipes[filtered_recipes['difficulty'] == user_difficulty_filter]
        
        if user_ingredients:
            ingredients = user_ingredients.split(',')
            for ingredient in ingredients:
                filtered_recipes = filtered_recipes[filtered_recipes['ingredients_combined'].str.contains(ingredient.strip())]

            suggested_recipes = suggest_random_recipes(filtered_recipes, 5)

            if suggested_recipes.empty:
                st.warning("No recipes at Chez Ratatouille match your criteria.")
            else:
                st.subheader("Suggested Recipes from the Chef's Mind:")
                for idx, row in suggested_recipes.iterrows():
                    st.image(row['image_url'], width=200, caption=row['title'])
                    recipe_button_label = f"Select {row['title']}"
                    st.button("Download Recipe PDF")
                    if st.button("Download Recipe PDF"):
                        # Define a filename for the PDF
                        pdf_filename = f"{selected_recipe['title'].replace(' ', '_')}_recipe.pdf"

                        # Create a PDF with the selected recipe
                        save_single_recipe_to_pdf(selected_recipe, pdf_filename)

                        # Provide a download link for the PDF
                        st.markdown(f"Download the recipe as a PDF: [Download Recipe PDF]({pdf_filename})")


with col3:
    st.header("Generate Meal Plan")
    
    # Allow the user to select the number of days
    num_days = st.number_input("How many days do you want Chef Ratatouille to prepare the meal plan for?", min_value=1, value=7, step=1, format="%d")
    
    # Create empty lists to store user input for each day
    meal_classes = []
    cost = []
    difficulty = []
    max_time = []

    # Loop through each day to get user input
    for day in range(1, num_days + 1):
        st.subheader(f"Day {day} Preferences")
        
        # Allow users to select meal classes for each day
        meal_classes = st.multiselect(f"Select Meal Classes for Day {day}",
            ["Entradas e Petiscos", "Sopas", "Saladas", "Peixes", "Carnes", "Acompanhamentos", "Doces e Sobremesas", "Entradas e Petiscos", "Vegetariano"])
        meal_classes.append(meal_classes)

        # Allow users to select cost and difficulty options for each day
        cost = st.selectbox(f"Select Cost for Day {day}", ["Económico", "Médio", "Dispendioso"])
        difficulty = st.selectbox(f"Select Difficulty for Day {day}", ["Fácil", "Médio", "Difícil"])

        # Allow users to set a maximum cooking time for each day
        max_time = st.number_input(f"Cooking Time (minutes) for Day {day}", min_value=1, value=60)

    if st.button("Generate Meal Plan"):
        meal_plan = generate_meal_plan_with_user_preferences(num_days, df)
        map = map_categorical_to_cosine(meal_plan)
        avg_cosine_similarity = calculate_avg_cosine_similarity(map)
        highest_similarity_recipes = find_highest_similarity_recipes(df, avg_cosine_similarity)
        st.subheader("The Chef suggests this Meal Plan:")
        for day, info in highest_similarity_recipes.items():
            day_parts = day.split(': ')
            day_of_recipe = day_parts[0]
            meal_class = day_parts[1]
            title = info.get('title')
            st.write(f"Day of recipe: {day_of_recipe}")
            st.write(f"Meal Class: {meal_class}")
            st.write(f"Title of Recipe: {title}")
                
    if st.button("Generate PDF"):
        save_meal_plan_to_pdf(highest_similarity_recipes, df, num_days)
        st.success("Chef Ratatouille has prepared a PDF file for you! Thank you for using Chez Ratatouille! Enjoy your meal!")
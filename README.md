# 🗑️ Friend Slop Site 🐷

## 🧑‍🍳 Chief Slop Officers (Team)

* Volodymyr Melnyk
* Oleksandr Skoromnov

## 📜 Project Topic

**Friend Slop Site (Private Social Trough)** — a highly exclusive, VIP-only web application designed for us to dump our
collective brainrot and shared hobbies into one digital pigsty. It's a repository for our recipes, video game backlog,
and workout routines.

## 🐽 Description & Features

This project is our shared digital landfill. It's a secure platform where we can dump our favorite recipes, complain
about the video games we play, and plan our desperate attempts to stay in shape. The trough is completely private and
requires mandatory authentication (no randoms allowed in our slop, strictly no guest access).

**The Core Slop:**

* 🍳 **Culinary Slop (Recipes):** Dump your favorite unhinged recipes here. We rate and review the terrible cooking we
  dump here, and everyone else can leave comments.
* 🎮 **Digital Slop (Video Games):** Maintain a backlog of games we've played or pretend we're going to play. Each of us
  tracks our own status, rates games and writes scathing reviews.
* 🏋️ **Sweaty Slop (Workouts):** Describe exercises, paste links to fitness videos that we will probably ignore, and
  assemble them into workout plans. Plans we don't favourite quietly rot away after some time.
* 🎲 **Slop Roulette (Randomizers):** Too lazy to decide? Let the trough decide for you.
    * **Food:** NAIVE mode throws random ingredients together; SMART mode builds coherent combinations based on how
      often ingredients appear together in ~2.2M real recipes from RecipeNLG.
    * **Games:** Random game filtered by genre and status.
    * **Training:** Random plan built from muscle category, load category and intensity.

**✨ Premium Algorithmic Slop:**
Because we are too lazy to do manual data entry, the trough integrates with Third-Party APIs to do the heavy lifting:

* **RAWG API (or IGDB):** We can't even be bothered to write game descriptions. Just type the game name, and our backend
  slurps up the official cover art, release date, and synopsis directly from the API.
* **YouTube API:** Looking at raw URLs is too hard for our TikTok-fried attention spans. When a YouTube link is tossed
  into an exercise, the backend automatically extracts the video title, duration, and thumbnail to make the UI pop.

## ⚙️ The Slop Infrastructure

* **Architecture:** Client-server using REST API (principles followed, mostly).
* **Database:** A robust PostgreSQL database holds all our recipes, game logs, workout plans, user data, and toxic
  reviews.
* **Security:** Secured tighter than Fort Knox with JWT Authentication. No guest access is provided.
* **Roles & Permissions:**
    * 👑 **Admin (Slop Master):** Both of us. Full god-mode access to the system. Can create recipes, add games, build
      workout plans, banish users, and purge the database.
    * 🐖 **User (Slop Consumer):** Read-only access to the trough, with the singular privilege of leaving scathing
      comments on our recipes.

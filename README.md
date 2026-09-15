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
about the video games we play, and log our desperate attempts to stay in shape. The trough is completely private and
requires mandatory authentication (no randoms allowed in our slop, strictly no guest access).

**The Core Slop:**

* 🍳 **Culinary Slop (Recipes):** Dump your favorite unhinged recipes here. Includes the ability to rate, review, and
  judge each other's terrible cooking.
* 🎮 **Digital Slop (Video Games):** Maintain a backlog of games we've played or pretend we're going to play. Rate games
  and write scathing reviews.
* 🏋️ **Sweaty Slop (Workouts):** Create workout plans with detailed descriptions and paste links to fitness videos that
  we will probably ignore.

**✨ Premium Algorithmic Slop:**
Because we are too lazy to do manual data entry, the trough integrates with Third-Party APIs to do the heavy lifting:

* **RAWG API (or IGDB):** We can't even be bothered to write game descriptions. Just type the game name, and our backend
  slurps up the official cover art, release date, and synopsis directly from the API.
* **YouTube API:** Looking at raw URLs is too hard for our TikTok-fried attention spans. When a YouTube link is tossed
  into a workout plan, the backend automatically extracts the video title, duration, and thumbnail to make the UI pop.

## ⚙️ The Slop Infrastructure

* **Architecture:** Client-server using REST API (principles followed, mostly).
* **Database:** A robust PostgreSQL database holds all our recipes, game logs, workout plans, user data, and toxic
  reviews.
* **Security:** Secured tighter than Fort Knox with JWT Authentication. No guest access is provided.
* **Roles & Permissions:**
    * 👑 **Admin (Slop Master):** Has full god-mode access to the system. Can create recipes, add games, build workout
      plans, banish users, and purge the database.
    * 🐖 **User (Slop Consumer):** Read-only access to the trough, with the singular privilege of leaving scathing
      reviews and ratings on the Admin's slop.

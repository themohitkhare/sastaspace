package main

import "os"

type Config struct {
	Port        string
	DatabaseURL string
}

func loadConfig() Config {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgres://postgres:devpassword@localhost:5432/sastaspace"
	}

	return Config{Port: port, DatabaseURL: dbURL}
}

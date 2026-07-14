package auth

import (
	"sync"
	"time"
)

type TokenInfo struct {
	Username  string
	ExpiresAt time.Time
}

var (
	tokens = make(map[string]TokenInfo)
	mu     sync.RWMutex
)

func SaveToken(token string, username string) {
	mu.Lock()
	defer mu.Unlock()

	tokens[token] = TokenInfo{
		Username:  username,
		ExpiresAt: time.Now().Add(1 * time.Hour),
	}
}

func ValidateToken(token string) bool {
	mu.RLock()
	defer mu.RUnlock()

	tokenInfo, exists := tokens[token]

	if !exists {
		return false
	}

	if time.Now().After(tokenInfo.ExpiresAt) {
		return false
	}

	return true
}

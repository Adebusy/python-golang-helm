package middleware

import (
	"net/http"
	"strings"

	"github.com/Adebusy/infrastore/auth"
	"github.com/gin-gonic/gin"
)

func AuthMiddleware() gin.HandlerFunc {
	return func(ctx *gin.Context) {
		authHeader :=
			ctx.GetHeader("Authorization")

		if authHeader == "" {
			ctx.JSON(http.StatusUnauthorized, gin.H{
				"error": "authorization header required",
			})
			ctx.Abort()
			return
		}

		parts := strings.SplitN(
			authHeader,
			" ",
			2,
		)

		if len(parts) != 2 ||
			parts[0] != "Token" {

			ctx.JSON(http.StatusUnauthorized, gin.H{
				"error": "invalid authorization header",
			})
			ctx.Abort()
			return
		}

		token := parts[1]

		if !auth.ValidateToken(token) {
			ctx.JSON(http.StatusUnauthorized, gin.H{
				"error": "invalid or expired token",
			})
			ctx.Abort()
			return
		}

		ctx.Next()
	}
}

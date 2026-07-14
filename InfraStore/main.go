package main

import (
	"database/sql"
	"log"
	"net/http"
	"os"

	"github.com/Adebusy/infrastore/dataaccess"
	httpHandler "github.com/Adebusy/infrastore/http"
	"github.com/Adebusy/infrastore/middleware"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	godotenv.Load()
	db, err := sql.Open(
		"sqlite3",
		"./db/infrastore.db",
	)

	if err != nil {
		log.Fatal(err)
	}

	defer db.Close()

	fileRepository :=
		dataaccess.NewFileRepository(db)

	if err := fileRepository.CreateTable(); err != nil {
		log.Fatal(err)
	}

	uploadHandler :=
		httpHandler.NewUploadHandler(fileRepository)

	svc := gin.Default()

	protected := svc.Group("/api")

	protected.Use(
		middleware.AuthMiddleware(),
	)

	protected.POST("/upload/", uploadHandler.Upload)
	svc.POST("api/token/", uploadHandler.Token) //Obtain a token for authentication
	protected.GET("/files/", uploadHandler.GetFiles)
	protected.GET("/filesbyId/:id", uploadHandler.GetFileBYID)
	protected.DELETE("/files/:id", uploadHandler.DeleteFileBYID)
	svc.GET("/", CheckServiceStatus)

	svc.Run(os.Getenv("AppPort"))
}

func CheckServiceStatus(ctx *gin.Context) {
	ctx.JSON(http.StatusOK, "I am up and running!!!")
}

// func init() {
// 	db, err := sql.Open(
// 		"sqlite3",
// 		"./db/infrastore.db",
// 	)

// 	if err != nil {
// 		log.Fatal(err)
// 	}

// 	defer db.Close()

// 	fileRepository :=
// 		dataaccess.NewFileRepository(db)

// 	if err := fileRepository.CreateTable(); err != nil {
// 		log.Fatal(err)
// 	}
// }

// func Init() (*httpHandler.UploadHandler, *gin.Engine, *gin.RouterGroup) {
// 	db, err := sql.Open(
// 		"sqlite3",
// 		"./db/infrastore.db",
// 	)

// 	if err != nil {
// 		log.Fatal(err)
// 	}

// 	defer db.Close()

// 	fileRepository :=
// 		dataaccess.NewFileRepository(db)

// 	if err := fileRepository.CreateTable(); err != nil {
// 		log.Fatal(err)
// 	}

// 	uploadHandler :=
// 		httpHandler.NewUploadHandler(fileRepository)

// 	svc := gin.Default()

// 	protected := svc.Group("/api")

// 	protected.Use(
// 		middleware.AuthMiddleware(),
// 	)
// 	return uploadHandler, svc, protected
// }

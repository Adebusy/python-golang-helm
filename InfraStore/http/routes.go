package http

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"net/http"
	"os"
	"strconv"

	"github.com/Adebusy/infrastore/dataaccess"
	"github.com/Adebusy/infrastore/model"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"

	_ "github.com/mattn/go-sqlite3"

	"github.com/Adebusy/infrastore/auth"
)

type UploadHandler struct {
	Repository *dataaccess.FileRepository
}

func NewUploadHandler(
	repository *dataaccess.FileRepository,
) *UploadHandler {
	return &UploadHandler{
		Repository: repository,
	}
}

func (handler *UploadHandler) Upload(ctx *gin.Context) {
	// var request model.File

	file, err := ctx.FormFile("file")
	if err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"error": "file is required",
		})
		return
	}

	filePath := "./media/" + file.Filename

	if err := ctx.SaveUploadedFile(file, filePath); err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"error": "failed to save file",
		})
		return
	}

	id, err := handler.Repository.Create(file.Filename, filePath)

	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"error": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusCreated, gin.H{
		"message": "file record created successfully",
		"id":      id,
	})
}

func (handler *UploadHandler) GetFiles(ctx *gin.Context) {
	files, err := handler.Repository.GetAllFile()
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"error": "failed to retrieve files",
		})
		return
	}
	ctx.JSON(http.StatusOK, files)
}

func (handler *UploadHandler) DeleteFileBYID(ctx *gin.Context) {
	idParam := ctx.Param("id")

	id, err := strconv.ParseInt(
		idParam,
		10,
		64,
	)

	if err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"error": err.Error(),
		})
		return
	}

	errs := handler.Repository.DeleteByID(id)
	if errs != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"error": errs.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, "Record deleted successfully")
}

func (handler *UploadHandler) GetFileBYID(ctx *gin.Context) {
	idParam := ctx.Param("id")

	id, err := strconv.ParseInt(
		idParam,
		10,
		64,
	)

	if err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"error": err.Error(),
		})
		return
	}

	file, errs := handler.Repository.GetByID(id)
	if errs != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"error": errs.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, file)
}

func (handler *UploadHandler) Token(ctx *gin.Context) {

	if loadEnv := godotenv.Load(); loadEnv != nil {
		ret := fmt.Sprintf("Unable to load environment variable. %s", loadEnv.Error())
		fmt.Println(ret)
	}

	var request model.TokenRequest

	if err := ctx.ShouldBind(&request); err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"error": "invalid request",
		})
		return
	}

	adminUsername := os.Getenv("DJANGO_SUPERUSER_USERNAME")
	adminPassword := os.Getenv("DJANGO_SUPERUSER_PASSWORD")

	if request.Username != adminUsername || request.Password != adminPassword {
		ctx.JSON(http.StatusUnauthorized, gin.H{
			"error": "invalid username or password",
		})
		return
	}

	token, err := generateToken()
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"error": "failed to generate token",
		})
		return
	}

	//save token
	auth.SaveToken(
		token,
		request.Username,
	)

	ctx.JSON(http.StatusOK, gin.H{
		"token": token,
	})
}

func generateToken() (string, error) {
	bytes := make([]byte, 32)

	_, err := rand.Read(bytes)
	if err != nil {
		return "", err
	}

	return hex.EncodeToString(bytes), nil
}

package model

type File struct {
	ID       int64  `json:"id"`
	FileName string `json:"file_name"`
	FilePath string `json:"file_path"`
}

type TokenRequest struct {
	Username string `form:"username" json:"username"`
	Password string `form:"password" json:"password"`
}

package dataaccess

import (
	"database/sql"
	"fmt"

	"github.com/Adebusy/infrastore/model"
)

type FileRepository struct {
	DB *sql.DB
}

func NewFileRepository(db *sql.DB) *FileRepository {
	return &FileRepository{
		DB: db,
	}
}

func (repository *FileRepository) CreateTable() error {
	query := `
		CREATE TABLE IF NOT EXISTS files (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			file_name TEXT NOT NULL,
			file_path TEXT NOT NULL
		);
	`

	_, err := repository.DB.Exec(query)

	if err != nil {
		return fmt.Errorf("failed to create files table: %w", err)
	}

	return nil
}

func (repository *FileRepository) Create(fileName, filePath string) (int64, error) {
	query := `
		INSERT INTO files (
			file_name,
			file_path
		)
		VALUES (?, ?)
	`

	result, err := repository.DB.Exec(
		query,
		fileName,
		filePath,
	)

	if err != nil {
		return 0, fmt.Errorf("failed to insert file: %w", err)
	}

	id, err := result.LastInsertId()

	if err != nil {
		return 0, fmt.Errorf(
			"failed to retrieve inserted ID: %w",
			err,
		)
	}

	return id, nil
}

func (repository *FileRepository) GetByID(id int64) (*model.File, error) {
	query := `
		SELECT
			id,
			file_name,
			file_path
		FROM files
		WHERE id = ?
	`

	file := &model.File{}

	err := repository.DB.QueryRow(
		query,
		id,
	).Scan(
		&file.ID,
		&file.FileName,
		&file.FilePath,
	)

	if err != nil {
		return nil, err
	}

	return file, nil
}

func (repository *FileRepository) GetAllFile() ([]model.File, error) {
	query := `
		SELECT
			id,
			file_name,
			file_path
		FROM files
	`
	rows, err := repository.DB.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	files := []model.File{}

	for rows.Next() {
		var file model.File

		err := rows.Scan(
			&file.ID,
			&file.FileName,
			&file.FilePath,
		)

		if err != nil {
			return nil, err
		}

		files = append(files, file)
	}

	if err := rows.Err(); err != nil {
		return nil, err
	}

	return files, nil
}

func (repository *FileRepository) DeleteByID(id int64) error {
	query := `DELETE FROM files WHERE id = ?`

	result, err := repository.DB.Exec(query, id)
	if err != nil {
		return err
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return err
	}

	if rowsAffected == 0 {
		return sql.ErrNoRows
	}

	return nil
}

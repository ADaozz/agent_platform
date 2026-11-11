package org.example.backend.auth.session.dto;

import lombok.Data;

@Data
public class LoginSessionQueryDTO {

    private Long userId;

    private String userName;

    private Integer pageNum;

    private Integer pageSize;
}

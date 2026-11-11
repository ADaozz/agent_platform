package org.example.backend.auth.cert.dto;

import lombok.Data;

@Data
public class UserCertQueryDTO {

    private String userName;

    private String certType;

    private String status;

    private Integer pageNum;

    private Integer pageSize;
}

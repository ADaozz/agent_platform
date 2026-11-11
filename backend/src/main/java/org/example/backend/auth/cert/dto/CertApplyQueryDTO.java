package org.example.backend.auth.cert.dto;

import lombok.Data;

@Data
public class CertApplyQueryDTO {

    private String userName;

    private String status;

    private Integer pageNum;

    private Integer pageSize;
}

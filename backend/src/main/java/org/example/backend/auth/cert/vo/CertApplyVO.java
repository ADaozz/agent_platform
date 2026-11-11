package org.example.backend.auth.cert.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;
import org.springframework.format.annotation.DateTimeFormat;

import java.util.Date;
import java.util.List;

@Data
public class CertApplyVO {

    private Long applyId;

    private Long userId;

    private String userName;

    private String applyType;

    private String status;

    private String applyReason;

    private String rejectReason;

    private String subjectCn;

    private String subjectO;

    private String subjectOu;

    private Integer validDays;

    private Long approverId;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date approveTime;

    /** 是否仍可领取 P12 密码（审批通过后、用户尚未查看时为 true） */
    private boolean p12PasswordPending;

    private boolean downloadable;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date createTime;

    private List<UserCertVO> issuedCerts;
}

package org.example.backend.system.user.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.experimental.Accessors;
import org.springframework.format.annotation.DateTimeFormat;

import java.util.Date;
import java.util.List;

@Data
@TableName("sys_user")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class SysUserEntity {

    @TableId(type = IdType.ASSIGN_ID)
    // 用户 ID
    private Long userId;

    // 用户名
    private String userName;

    // 密码（加密存储）
    private String passWord;

    // 用户状态：0-正常，1-停用
    private String status;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 创建时间
    private Date createTime;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 更新时间
    private Date updateTime;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 最后登录时间
    private Date lastLoginTime;

}

package org.example.backend.api.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.experimental.Accessors;
import org.springframework.format.annotation.DateTimeFormat;

import java.util.Date;
import java.util.List;

@Data
@TableName(value = "api_token", autoResultMap = true)
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class ApiTokenEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    // 访问密钥 AK，公开标识，也是 Token 主键
    private String accessKey;

    // 所属用户 ID
    private Long userId;

    // Token 名称
    private String tokenName;

    // Token 用途说明
    private String detail;

    @TableField(typeHandler = JacksonTypeHandler.class)
    // 授权业务资源：vm:list / vm:add / vm:edit / vm:delete、app:*；兼容旧值 vm、app（等同 list）
    private List<String> asset;

    // 私密密钥 SK，仅创建时返回给用户
    private String secretKey;

    // Token 状态：0-正常，1-已吊销
    private String status;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 过期时间
    private Date expireTime;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 创建时间
    private Date createTime;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 更新时间
    private Date updateTime;
}

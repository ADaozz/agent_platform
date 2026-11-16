package org.example.backend.system.role.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.example.backend.common.vo.OptionVO;
import org.example.backend.system.role.entity.SysRoleEntity;

import java.util.List;

public interface SysRoleMapper extends BaseMapper<SysRoleEntity> {

    /** Kingbase 下 sys_role 等为同名系统 catalog，须限定 public；SQLite 无 schema */
    String SCHEMA_BIND = "<bind name='sch' value=\"_databaseId == 'kingbase' ? 'public.' : ''\"/>";

    @Select("<script>" + SCHEMA_BIND
            + "SELECT DISTINCT r.sys_role "
            + "FROM ${sch}sys_user_role ur "
            + "JOIN ${sch}sys_role r ON ur.role_id = r.role_id "
            + "WHERE ur.user_id = #{userId}"
            + "</script>")
    List<String> selectSysRoleByUserId(@Param("userId") Long userId);

    @Select("<script>" + SCHEMA_BIND
            + "SELECT DISTINCT r.role_id AS id, r.sys_role AS label "
            + "FROM ${sch}sys_user_role ur "
            + "JOIN ${sch}sys_role r ON ur.role_id = r.role_id "
            + "WHERE ur.user_id = #{userId}"
            + "</script>")
    List<OptionVO> selectRoleOptionsByUserId(@Param("userId") Long userId);

    @Select("<script>" + SCHEMA_BIND
            + "SELECT role_id AS id, sys_role AS label "
            + "FROM ${sch}sys_role ORDER BY role_id"
            + "</script>")
    List<OptionVO> selectAllRoleOptions();
}

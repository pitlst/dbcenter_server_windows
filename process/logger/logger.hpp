#ifndef DBS_LOGGER_INCLUDE
#define DBS_LOGGER_INCLUDE

#include <memory>
#include <string>

#include "mongo.hpp"

namespace dbs{

    // 全局单例的日志类，用于组织日志相关的io操作
    class logger
    {
    public:
        // 获取单实例对象
        static logger &instance();
        // 不同等级日志
        void debug(const std::string & name, const std::string & msg);
        void info(const std::string & name, const std::string & msg);
        void warn(const std::string & name, const std::string & msg);
        void error(const std::string & name, const std::string & msg);
        void emit(const std::string & level, const std::string & name, const std::string & msg);
    private:
        // 禁止外部构造与析构
        logger();
        ~logger();
        // 获取当前时间的字符串
        std::string get_time_str(const std::chrono::system_clock::time_point & input_time) const;

        // 数据库客户端
        const std::string db_name = "logger";
        std::unique_ptr<mongocxx::pool::entry> m_client_ptr;
        std::unique_ptr<mongocxx::database> m_database_ptr;
    };
}

#endif